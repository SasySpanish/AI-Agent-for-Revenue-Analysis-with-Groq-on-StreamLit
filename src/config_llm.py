# config_llm.py  
# Gestione centralizzata del modello LLM e della API key Groq.
# Importato da tutti gli altri moduli al posto di istanziare
# ChatGroq direttamente.

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Carica le variabili d'ambiente dal file .env
load_dotenv()


# ---------------------------------------------------------------------------
# CONFIGURAZIONE MODELLI
# ---------------------------------------------------------------------------

# Modello principale — tool use affidabile, veloce, gratuito
PRIMARY_MODEL = "llama-3.3-70b-versatile"

# Modello fallback — più leggero, utile se si raggiunge il rate limit
FALLBACK_MODEL = "llama-3.1-8b-instant"

# Modello per il report discorsivo — stesso del principale
REPORT_MODEL = "llama-3.3-70b-versatile"


# ---------------------------------------------------------------------------
# FACTORY FUNCTIONS
# ---------------------------------------------------------------------------

def get_llm(temperature: float = 0) -> ChatGroq:
    """
    Restituisce il modello principale configurato per tool use.
    temperature=0 per massima determinismo nelle chiamate ai tool.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY non trovata. "
            "Assicurati che il file .env contenga: GROQ_API_KEY=la_tua_chiave"
        )

    return ChatGroq(
        model=PRIMARY_MODEL,
        api_key=api_key,
        temperature=temperature,
        max_tokens=4096,
    )


def get_report_llm() -> ChatGroq:
    """
    Restituisce il modello per la generazione del testo discorsivo.
    Usa temperature più alta per un testo più naturale e vario.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY non trovata. "
            "Assicurati che il file .env contenga: GROQ_API_KEY=la_tua_chiave"
        )

    return ChatGroq(
        model=REPORT_MODEL,
        api_key=api_key,
        temperature=0.4,
        max_tokens=8192,   # report più lunghi e dettagliati
    )


def get_fallback_llm() -> ChatGroq:
    """
    Modello leggero da usare in caso di rate limit sul modello principale.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY non trovata.")

    return ChatGroq(
        model=FALLBACK_MODEL,
        api_key=api_key,
        temperature=0,
        max_tokens=4096,
    )


# ---------------------------------------------------------------------------
# VERIFICA CONNESSIONE
# ---------------------------------------------------------------------------

def test_connection() -> bool:
    """
    Verifica che la API key sia valida e il modello risponda.
    Usata da phase2_check.py.
    """
    try:
        llm      = get_llm()
        response = llm.invoke("Reply with exactly: GROQ_OK")
        return "GROQ_OK" in response.content
    except Exception as e:
        print(f"  Errore connessione Groq: {e}")
        return False


# ---------------------------------------------------------------------------
# VERIFICA RAPIDA SE LANCIATO DIRETTAMENTE
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Testing Groq connection...")
    if test_connection():
        print("✅ Groq API key valida — modello risponde correttamente")
        print(f"   Modello principale : {PRIMARY_MODEL}")
        print(f"   Modello report     : {REPORT_MODEL}")
        print(f"   Modello fallback   : {FALLBACK_MODEL}")
    else:
        print("❌ Connessione fallita — controlla la API key nel file .env")