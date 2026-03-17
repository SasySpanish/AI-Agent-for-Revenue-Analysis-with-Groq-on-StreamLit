# agent.py  
# Agente vero con tool use autonomo — llama-3.3-70b via Groq.
# Il modello decide autonomamente quali tool chiamare e in quale ordine.

import sys
import os
import json

# ---------------------------------------------------------------------------
# PATH — permette di importare i moduli di wheelhouse
# ---------------------------------------------------------------------------

WHEELHOUSE_PATH = r"C:/Users/Utente/Desktop/revenuescript"
if WHEELHOUSE_PATH not in sys.path:
    sys.path.insert(0, WHEELHOUSE_PATH)

# ---------------------------------------------------------------------------
# IMPORT
# ---------------------------------------------------------------------------

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from config_llm       import get_llm
from ticker_resolver  import ticker_resolver_tool, validate_custom_tickers_tool
from tool_analysis    import run_analysis_tool
from report_generator import generate_report_tool

load_dotenv()


# ---------------------------------------------------------------------------
# SYSTEM PROMPT
# ---------------------------------------------------------------------------

AGENT_SYSTEM_PROMPT = """You are a financial analysis agent powered by 
llama-3.3-70b. Your goal is to help users analyse companies and sectors 
using fundamental financial data.

## Available tools
- **ticker_resolver_tool**: use when the user describes companies or sectors 
  in natural language (e.g. "European banks", "top automotive OEMs", 
  "banche europee", "big tech us"). Returns a JSON with resolved tickers.
- **validate_custom_tickers_tool**: use when the user provides explicit 
  ticker symbols separated by commas (e.g. "BMW.DE, AAPL, UCG.MI"). 
  Returns a JSON with validated tickers.
- **run_analysis_tool**: ALWAYS call after resolving tickers. 
  Pass the COMPLETE JSON string from the resolver as input.
  Downloads financial data, computes indicators, generates charts.
- **generate_report_tool**: ALWAYS call last. 
  Pass the COMPLETE JSON string from run_analysis_tool as input.
  Generates HTML and PDF reports with analyst commentary.

## Strict workflow — always follow this order
1. Resolve tickers → ticker_resolver_tool OR validate_custom_tickers_tool
2. Run analysis   → run_analysis_tool (pass full JSON from step 1)
3. Generate report → generate_report_tool (pass full JSON from step 2)
4. Tell the user where the output files are saved

## Rules
- Never skip any step
- Always pass the complete JSON output from one tool as input to the next
- If a ticker cannot be resolved, ask the user for clarification
- If the analysis fails for a ticker, continue with the others
- Respond in the same language the user used
- Be concise in your final response — just confirm what was done and 
  where the files are saved

## Sector keywords recognised
- automotive europeo → VW, Stellantis, Mercedes, BMW, Renault, Porsche, Volvo Cars, TRATON, Iveco
- banche europee → UniCredit, Intesa, BNP, Santander, Deutsche Bank, HSBC, Barclays, SocGen, ING
- big tech us → Apple, Microsoft, Alphabet, Amazon, Meta, Nvidia
- semiconduttori / semiconductors / chips → Nvidia, TSMC, ASML, Intel, AMD, Broadcom, Qualcomm, STMicro, Infineon, Applied Materials, KLA, Lam Research
- pharma / farmaceutico / healthcare → Eli Lilly, Novo Nordisk, AbbVie, J&J, Roche, Novartis, AstraZeneca, Sanofi, Pfizer, Merck, BioNTech
- telecomunicazioni / telecom / telco → AT&T, Verizon, T-Mobile, Deutsche Telekom, Vodafone, Orange, Telefonica, Telecom Italia, Swisscom
- aerospace defense / difesa → Boeing, Airbus, Lockheed Martin, Raytheon, Northrop Grumman, General Dynamics, BAE Systems, Leonardo, Safran, Thales, Rolls-Royce
- food beverage / cibo → Nestlé, Unilever, Danone, AB InBev, Diageo, PepsiCo, Coca-Cola, Mondelez, Kraft Heinz, Campari
- lusso / luxury / fashion / moda → LVMH, Hermès, Kering, Richemont, Ferrari, Moncler, Brunello Cucinelli, Burberry, Hugo Boss, Tod's, Ferragamo
- asset management / fintech / gestione → BlackRock, Blackstone, Goldman Sachs, Morgan Stanley, Visa, Mastercard, PayPal, Block, FinecoBank, Azimut
- ftse mib / italia / italy → Enel, Eni, UniCredit, Intesa, Ferrari, Generali, Moncler, Mediobanca, Prysmian, Campari, Amplifon, Recordati
"""

# Prompt ReAct — struttura obbligatoria per AgentExecutor
REACT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", AGENT_SYSTEM_PROMPT),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])


# ---------------------------------------------------------------------------
# BUILD AGENT
# ---------------------------------------------------------------------------

def build_agent():
    llm   = get_llm(temperature=0)
    tools = [
        ticker_resolver_tool,
        validate_custom_tickers_tool,
        run_analysis_tool,
        generate_report_tool,
    ]

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=AGENT_SYSTEM_PROMPT,
    )
    return agent


# ---------------------------------------------------------------------------
# PIPELINE DI FALLBACK
# Usata automaticamente se l'agente non completa il workflow autonomamente
# ---------------------------------------------------------------------------

def run_pipeline_fallback(user_input: str):
    """
    Pipeline deterministico Python — identico al progetto precedente.
    Attivato solo se l'agente autonomo non produce output completo.
    """
    print("\n[fallback] Attivazione pipeline deterministico...\n")

    # Step 1
    resolver_result = ticker_resolver_tool.invoke({"query": user_input})
    data = json.loads(resolver_result)

    if not data.get("tickers"):
        resolver_result = validate_custom_tickers_tool.invoke(
            {"ticker_list": user_input}
        )
        data = json.loads(resolver_result)

    tickers = data.get("tickers") or data.get("valid", [])
    if not tickers:
        print(f"\n  Nessun ticker trovato per: '{user_input}'")
        print("  Prova con ticker espliciti, es: BMW.DE, UCG.MI, AAPL\n")
        return

    print(f"  Ticker: {tickers}")

    # Step 2
    analysis_result = run_analysis_tool.invoke(
        {"resolver_output": resolver_result}
    )
    analysis_data = json.loads(analysis_result)

    if analysis_data.get("status") != "success":
        print(f"\n  Analisi fallita: {analysis_data.get('error')}\n")
        return

    # Step 3
    report_result = generate_report_tool.invoke(
        {"analysis_output": analysis_result}
    )
    report_data = json.loads(report_result)

    if report_data.get("status") != "success":
        print(f"\n  Report fallito: {report_data.get('error')}\n")
        return

    files = report_data.get("files", {})
    print("\n✅ Analisi completata!")
    print(f"   HTML      : {files.get('html')}")
    print(f"   PDF       : {files.get('pdf')}")
    print(f"   Dashboard : {files.get('dashboard')}\n")


# ---------------------------------------------------------------------------
# LOOP INTERATTIVO
# ---------------------------------------------------------------------------

def run_interactive():
    print("\n" + "=" * 60)
    print("  WHEELHOUSE AGENT — Groq Edition")
    print("=" * 60)
    print(f"  Modello : llama-3.3-70b-versatile via Groq")
    print(f"  Output  : output_agent/")
    print("=" * 60)
    print("\nEsempi di prompt:")
    print("  → Analyse the top European automotive OEMs")
    print("  → Analyse European banks")
    print("  → Compare Apple, Microsoft and Nvidia")
    print("  → BMW.DE, MBG.DE, STLAM.MI")
    print("  → banche europee")
    print("\nDigita 'exit' per uscire.\n")

    agent = build_agent()

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nUscita.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("Uscita.")
            break

        print("\n[agent] Elaborazione in corso...\n")

        try:
            result = agent.invoke({
                "messages": [("human", user_input)]
            })
            messages = result.get("messages", [])
            output   = messages[-1].content if messages else ""

            if output and ("report.html" in output or
                           "output_agent" in output or
                           "saved" in output.lower() or
                           "generated" in output.lower()):
                print(f"\nAgent: {output}\n")
            else:
                print(f"\nAgent: {output}")
                print("\n[agent] Workflow incompleto — attivo fallback...\n")
                run_pipeline_fallback(user_input)

        except Exception as e:
            print(f"\n[agent] Errore agente: {e}")
            print("[agent] Attivo pipeline fallback...\n")
            run_pipeline_fallback(user_input)

        print("-" * 60)


# ---------------------------------------------------------------------------
# SINGLE SHOT
# ---------------------------------------------------------------------------

def run_once(prompt: str) -> dict:
    agent  = build_agent()
    result = agent.invoke({"messages": [("human", prompt)]})
    return result


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        print(f"\n[agent] Prompt: {prompt}\n")
        result = run_once(prompt)
        print(f"\nAgent: {result.get('output', '')}\n")
    else:
        run_interactive()