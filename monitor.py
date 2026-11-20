import hashlib
import json
import os
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from zoneinfo import ZoneInfo

ROMA_TZ = ZoneInfo("Europe/Rome")

SORGENTI_NAPOLI = [
    ("Avvisi Generali Comune", "https://www.comune.napoli.it/tipi_notizia/avviso/", "HTML"),
    ("Comunicati Stampa", "https://www.comune.napoli.it/tipi_notizia/comunicato-stampa/", "HTML"),
    ("Municipalita 1", "https://www.comune.napoli.it/amministrazione/unita_organizzativa/municipalita-1/", "HTML"),
    ("Municipalita 2", "https://www.comune.napoli.it/amministrazione/unita_organizzativa/municipalita-2/", "HTML"),
    ("Municipalita 3", "https://www.comune.napoli.it/amministrazione/unita_organizzativa/municipalita-3/", "HTML"),
    ("Municipalita 4", "https://www.comune.napoli.it/amministrazione/unita_organizzativa/municipalita-4/", "HTML"),
    ("Municipalita 5", "https://www.comune.napoli.it/amministrazione/unita_organizzativa/municipalita-5/", "HTML"),
    ("Municipalita 6", "https://www.comune.napoli.it/amministrazione/unita_organizzativa/municipalita-6/", "HTML"),
    ("Municipalita 7", "https://www.comune.napoli.it/amministrazione/unita_organizzativa/municipalita-7/", "HTML"),
    ("Municipalita 8", "https://www.comune.napoli.it/amministrazione/unita_organizzativa/municipalita-8/", "HTML"),
    ("Municipalita 9", "https://www.comune.napoli.it/amministrazione/unita_organizzativa/municipalita-9/", "HTML"),
    ("Municipalita 10", "https://www.comune.napoli.it/amministrazione/unita_organizzativa/municipalita-10/", "HTML"),
]

URL_PARACADUTE_GNEWS = (
    "https://news.google.com/rss/search?q=site:comune.napoli.it+"
    "(mercatini+OR+fiera+OR+fiere+OR+artigianato+OR+hobbisti+OR+posteggi+OR+ingegno+OR+antiquariato)"
    "&hl=it&gl=IT&ceid=IT:it"
)

ESCLUSIONI_FORTI = [
    "concorso pubblico",
    "mobilita volontaria",
    "alloggi erp",
    "fabbisogno abitativo",
    "asili nido",
    "sezioni primavera",
    "scuole dell'infanzia",
    "mensa scolastica",
    "dispositivo temporaneo di circolazione",
    "dispositivo di traffico",
    "sciopero generale",
    "monopattini elettrici",
    "stabilizzazione di personale",
    "dirigenti a tempo determinato",
    "polizia municipale",
    "servizio civile",
    "borse di studio",
    "buoni libro",
    "canone concordato",
    "mercato ittico",
    "mercato ortofrutticolo",
    "mercato agroalimentare",
]

PAROLE_CHIAVE = [
    "mercatin",
    "fiere",
    "fiera",
    "fieristic",
    "hobbist",
    "artigian",
    "proprio ingegno",
    "opere dell'ingegno",
    "opere del proprio ingegno",
    "pittur",
    "pittor",
    "artist",
    "antiquariat",
    "vintage",
    "collezionism",
    "postegg",
    "stall",
    "gazebo",
    "espositor",
    "non alimentar",
    "vendita occasionale",
    "natale 202",
    "mercatini di natale",
    "fiere di natale",
    "calendario mercat",
    "mostra mercato",
    "manufatt",
    "creativ",
]

MESI_IT = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5, "giugno": 6,
    "luglio": 7, "agosto": 8, "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
    "gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6,
    "lug": 7, "ago": 8, "set": 9, "ott": 10, "nov": 11, "dic": 12,
}


def adesso_roma():
    return datetime.now(ROMA_TZ)


def formatta_dt(dt):
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ROMA_TZ)
    else:
        dt = dt.astimezone(ROMA_TZ)
    return dt.strftime("%d/%m/%Y %H.%M")


def normalizza_url(url):
    if not url:
        return ""
    return url.strip().split("#")[0].rstrip("/")


def normalizza_titolo_chiave(titolo):
    pulito = re.sub(r"\s*[\|\u2013\u2014]\s*comune di napoli.*$", "", str(titolo or ""), flags=re.IGNORECASE)
    pulito = re.sub(r"[^a-z0-9\xe0\xe8\xe9\xec\xf2\xf9]+", " ", pulito.lower()).strip()
    return pulito[:90]


def pulisci_html(raw):
    if not raw:
        return ""
    senza_tag = re.sub(r"<[^>]+>", " ", str(raw))
    decodificato = unescape(senza_tag)
    return re.sub(r"\s+", " ", decodificato).strip()


def estrai_testo_leggibile(html):
    pulito = re.sub(r"<(script|style|noscript|nav|footer|header)[\s\S]*?</\1>", " ", html, flags=re.IGNORECASE)
    return pulisci_html(pulito)


def md5_testo(testo):
    return hashlib.md5(testo.encode("utf-8")).hexdigest()


def pausa_cortesia():
    time.sleep(random.uniform(3.5, 6.0))


def scarica_url(url, usa_browser=False):
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    if usa_browser:
        parsed = urllib.parse.urlparse(url)
        origine = f"{parsed.scheme}://{parsed.netloc}/" if parsed.netloc else url
        headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        headers["Referer"] = origine
        headers["Upgrade-Insecure-Requests"] = "1"
    else:
        headers["User-Agent"] = "MonitorBandiNapoli/1.0"

    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            codice = resp.getcode() or 200
            raw_bytes = resp.read()
            testo = raw_bytes.decode("utf-8", errors="replace")
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            return True, codice, testo, resp_headers
    except urllib.error.HTTPError as e:
        codice = e.code or 500
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return False, codice, body, {}
    except Exception as e:
        print(f"Errore rete su {url} {e}")
        return False, 0, "", {}


def scarica_con_tentativi(url):
    ok, code, body, headers = scarica_url(url, usa_browser=False)
    if not ok and code in (403, 406, 429):
        time.sleep(2.5)
        return scarica_url(url, usa_browser=True)
    return ok, code, body, headers


def ricava_titolo_da_slug(url):
    try:
        pulito = url.rstrip("/").split("?")[0]
        ultimo = urllib.parse.unquote(pulito.split("/")[-1] or "")
        return re.sub(r"\.pdf$", "", ultimo, flags=re.IGNORECASE).replace("_", " ").replace("-", " ").strip()
    except Exception:
        return ""


def supera_pre_filtro(titolo, url):
    testo = f"{titolo} {ricava_titolo_da_slug(url)}".lower()
    for esc in ESCLUSIONI_FORTI:
        if esc in testo:
            return False
    for kw in PAROLE_CHIAVE:
        if kw in testo:
            return True
    return False


def estrai_notizie_html(html, base_url):
    risultati = []
    visti = set()
    is_napoli = "comune.napoli.it" in base_url
    parsed_base = urllib.parse.urlparse(base_url)
    dominio_base = f"{parsed_base.scheme}://{parsed_base.netloc}"

    for m in re.finditer(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>', html, flags=re.IGNORECASE):
        href = (m.group(1) or "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        url_ass = urllib.parse.urljoin(base_url, href)
        url_norm = normalizza_url(url_ass)
        if not url_norm or url_norm in visti:
            continue

        if is_napoli:
            if "comune.napoli.it/novita/" not in url_norm or "/attachment/" in url_norm:
                continue
        else:
            if not url_norm.startswith(dominio_base):
                continue

        titolo = pulisci_html(m.group(2))
        if not titolo or len(titolo) < 18 or re.match(
            r"^(leggi|vai alla pagina|dettagli|approfondisci|scopri|continua|avviso|bando)\b",
            titolo,
            flags=re.IGNORECASE,
        ):
            da_slug = ricava_titolo_da_slug(url_norm)
            if len(da_slug) > len(titolo):
                titolo = da_slug

        if titolo and len(titolo) >= 10:
            visti.add(url_norm)
            risultati.append({"titolo": titolo, "url": url_norm, "descrizione_rss": "", "data_rss": ""})

    return risultati


def parsa_data_flessibile(raw):
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None

    m_iso = re.match(
        r"^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2})(?::(\d{2}))?(?:Z|[+-]\d{2}:?\d{2})?)?$",
        s,
    )
    if m_iso:
        ha_orario = bool(m_iso.group(4))
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ROMA_TZ)
            else:
                dt = dt.astimezone(ROMA_TZ)
            return dt, ha_orario
        except Exception:
            pass

    m_it = re.match(
        r"^(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})(?:\s+(?:alle\s+)?(\d{1,2})[.:](\d{2}))?$",
        s,
        flags=re.IGNORECASE,
    )
    if m_it:
        anno = int(m_it.group(3))
        if anno < 100:
            anno += 2000
        mese = int(m_it.group(2))
        giorno = int(m_it.group(1))
        ha_orario = bool(m_it.group(4))
        ora = int(m_it.group(4)) if ha_orario else 12
        minuto = int(m_it.group(5)) if ha_orario else 0
        try:
            dt = datetime(anno, mese, giorno, ora, minuto, 0, tzinfo=ROMA_TZ)
            return dt, ha_orario
        except Exception:
            pass

    m_txt = re.match(
        r"^(\d{1,2})\s+([a-z\xe0\xe8\xe9\xec\xf2\xf9]+)\s+(\d{4})(?:\s+(?:alle\s+)?(\d{1,2})[.:](\d{2}))?$",
        s.lower(),
    )
    if m_txt and m_txt.group(2) in MESI_IT:
        ha_orario = bool(m_txt.group(4))
        ora = int(m_txt.group(4)) if ha_orario else 12
        minuto = int(m_txt.group(5)) if ha_orario else 0
        try:
            dt = datetime(int(m_txt.group(3)), MESI_IT[m_txt.group(2)], int(m_txt.group(1)), ora, minuto, 0, tzinfo=ROMA_TZ)
            return dt, ha_orario
        except Exception:
            pass

    try:
        dt_rfc = parsedate_to_datetime(s)
        if dt_rfc:
            if dt_rfc.tzinfo is None:
                dt_rfc = dt_rfc.replace(tzinfo=timezone.utc)
            dt_rfc = dt_rfc.astimezone(ROMA_TZ)
            ha_orario = bool(re.search(r"\d{1,2}:\d{2}", s))
            return dt_rfc, ha_orario
    except Exception:
        pass

    return None


def formatta_data_parsata(parsed_tuple):
    if not parsed_tuple:
        return ""
    dt, ha_orario = parsed_tuple
    dt_it = dt.astimezone(ROMA_TZ)
    if ha_orario:
        return dt_it.strftime("%d/%m/%Y %H.%M")
    return dt_it.strftime("%d/%m/%Y") + " (ora non indicata dal sito)"


def estrai_notizie_rss(xml_text, base_url):
    risultati = []
    try:
        root = ET.fromstring(xml_text)
        channel = root.find("channel")
        if channel is not None:
            for item in channel.findall("item"):
                titolo = pulisci_html(item.findtext("title") or "")
                link = normalizza_url(urllib.parse.urljoin(base_url, (item.findtext("link") or "").strip()))
                desc = pulisci_html(item.findtext("description") or "")
                pub_raw = (item.findtext("pubDate") or "").strip()
                pub_parsed = parsa_data_flessibile(pub_raw)
                if link:
                    risultati.append({
                        "titolo": titolo,
                        "url": link,
                        "descrizione_rss": desc,
                        "data_rss": formatta_data_parsata(pub_parsed) if pub_parsed else "",
                    })
        else:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns):
                titolo = pulisci_html(entry.findtext("atom:title", namespaces=ns) or "")
                link_el = entry.find("atom:link", ns)
                href = (link_el.attrib.get("href") if link_el is not None else "") or ""
                link = normalizza_url(urllib.parse.urljoin(base_url, href.strip()))
                desc = pulisci_html(entry.findtext("atom:summary", namespaces=ns) or entry.findtext("atom:content", namespaces=ns) or "")
                pub_raw = (entry.findtext("atom:published", namespaces=ns) or entry.findtext("atom:updated", namespaces=ns) or "").strip()
                pub_parsed = parsa_data_flessibile(pub_raw)
                if link:
                    risultati.append({
                        "titolo": titolo,
                        "url": link,
                        "descrizione_rss": desc,
                        "data_rss": formatta_data_parsata(pub_parsed) if pub_parsed else "",
                    })
    except Exception as e:
        print(f"Errore parsing RSS {base_url} {e}")
    return risultati


def estrai_meta(html, nome):
    esc = re.escape(nome)
    m1 = re.search(rf'<meta[^>]+(?:property|name)=["\']{esc}["\'][^>]+content=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    if m1:
        return m1.group(1).strip()
    m2 = re.search(rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{esc}["\']', html, flags=re.IGNORECASE)
    if m2:
        return m2.group(1).strip()
    return ""


def estrai_date_pagina(html_completo, blocco_principale, headers):
    pub_raw = ""
    mod_raw = ""

    m_jp = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html_completo, flags=re.IGNORECASE)
    if m_jp:
        pub_raw = m_jp.group(1)
    m_jm = re.search(r'"dateModified"\s*:\s*"([^"]+)"', html_completo, flags=re.IGNORECASE)
    if m_jm:
        mod_raw = m_jm.group(1)

    if not pub_raw:
        pub_raw = estrai_meta(html_completo, "article:published_time") or estrai_meta(html_completo, "DC.date.issued") or estrai_meta(html_completo, "publishdate")
    if not mod_raw:
        mod_raw = estrai_meta(html_completo, "article:modified_time") or estrai_meta(html_completo, "og:updated_time") or estrai_meta(html_completo, "DC.date.modified")

    if not pub_raw:
        m_tm = re.search(r'<time[^>]*datetime=["\']([^"\']+)["\'][^>]*>', blocco_principale, flags=re.IGNORECASE)
        if m_tm:
            pub_raw = m_tm.group(1)

    testo_vis = estrai_testo_leggibile(blocco_principale)[:2500]
    if not pub_raw:
        m_pt = re.search(
            r"(?:pubblicat[oa]\s+il|data\s+di\s+pubblicazione|data\s+pubblicazione)[:\s]+"
            r"(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}(?:\s+(?:alle\s+)?\d{1,2}[.:]\d{2})?|\d{1,2}\s+[a-z\xe0\xe8\xe9\xec\xf2\xf9]+\s+\d{4}(?:\s+(?:alle\s+)?\d{1,2}[.:]\d{2})?)",
            testo_vis,
            flags=re.IGNORECASE,
        )
        if m_pt:
            pub_raw = m_pt.group(1)

    if not mod_raw:
        m_mt = re.search(
            r"(?:ultimo\s+aggiornamento|aggiornat[oa]\s+il|modificat[oa]\s+il|rettificat[oa]\s+il)[:\s]+"
            r"(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}(?:\s+(?:alle\s+)?\d{1,2}[.:]\d{2})?|\d{1,2}\s+[a-z\xe0\xe8\xe9\xec\xf2\xf9]+\s+\d{4}(?:\s+(?:alle\s+)?\d{1,2}[.:]\d{2})?)",
            testo_vis,
            flags=re.IGNORECASE,
        )
        if m_mt:
            mod_raw = m_mt.group(1)

    if not mod_raw and headers:
        mod_raw = headers.get("last-modified", "")

    pub_parsed = parsa_data_flessibile(pub_raw)
    mod_parsed = parsa_data_flessibile(mod_raw)

    ha_modifica = False
    if pub_parsed and mod_parsed:
        if (mod_parsed[0].timestamp() - pub_parsed[0].timestamp()) >= 900:
            ha_modifica = True

    return (
        formatta_data_parsata(pub_parsed) if pub_parsed else "",
        formatta_data_parsata(mod_parsed) if mod_parsed else "",
        ha_modifica,
    )


def analizza_dettaglio(url, titolo_fallback):
    if re.search(r"\.pdf(\?.*)?$", url, flags=re.IGNORECASE):
        nome_pdf = urllib.parse.unquote(url.split("?")[0].split("/")[-1] or "Allegato.pdf")
        return {
            "ok": True,
            "code": 200,
            "url": url,
            "titolo": titolo_fallback or nome_pdf,
            "testo": titolo_fallback or nome_pdf,
            "pdf_list": [{"nome": nome_pdf, "url": url}],
            "hash": md5_testo(url),
            "data_pub": "",
            "data_mod": "",
            "ha_modifica": False,
            "rettifica_titolo": bool(re.search(r"rettific|prorog|riapertura|errata corrige|integrazion", titolo_fallback or nome_pdf, flags=re.IGNORECASE)),
        }

    ok, code, html, headers = scarica_con_tentativi(url)
    if not ok:
        return {"ok": False, "code": code}

    titolo = titolo_fallback
    m_h1 = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", html, flags=re.IGNORECASE)
    if m_h1:
        h1_p = pulisci_html(m_h1.group(1))
        if len(h1_p) >= 10:
            titolo = h1_p
    else:
        m_t = re.search(r"<title[^>]*>([\s\S]*?)</title>", html, flags=re.IGNORECASE)
        if m_t:
            t_p = re.sub(r"\s*[\|\u2013\u2014]\s*Comune di.*$", "", pulisci_html(m_t.group(1)), flags=re.IGNORECASE).strip()
            if len(t_p) >= 10:
                titolo = t_p

    blocco = html
    m_main = re.search(r"<(main|article)[^>]*>([\s\S]*?)</\1>", html, flags=re.IGNORECASE)
    if m_main:
        blocco = m_main.group(2)

    m_corr = re.search(r"Contenuti correlati|Potrebbe interessarti|Ultime notizie", blocco, flags=re.IGNORECASE)
    if m_corr and m_corr.start() > 300:
        blocco = blocco[: m_corr.start()]

    data_pub, data_mod, ha_modifica = estrai_date_pagina(html, blocco, headers)

    pdf_list = []
    pdf_visti = set()
    for m_pdf in re.finditer(r'<a\s+[^>]*href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\'][^>]*>([\s\S]*?)</a>', blocco, flags=re.IGNORECASE):
        pdf_url = urllib.parse.urljoin(url, (m_pdf.group(1) or "").strip())
        if pdf_url not in pdf_visti:
            pdf_visti.add(pdf_url)
            label = pulisci_html(m_pdf.group(2))
            nome = label if (label and len(label) >= 4 and not re.match(r"^(scarica|download|pdf)$", label, flags=re.IGNORECASE)) else (
                urllib.parse.unquote(pdf_url.split("?")[0].split("/")[-1] or "Allegato.pdf")
            )
            pdf_list.append({"nome": nome, "url": pdf_url})

    testo_pulito = estrai_testo_leggibile(blocco)[:5000]
    firma_pdf = "\n".join(sorted(f"{p['nome']}:{p['url']}" for p in pdf_list))
    firma_testo = re.sub(r"\s+", " ", testo_pulito[:1800]).strip()
    impronta = md5_testo(f"{firma_pdf}||{firma_testo}")

    return {
        "ok": True,
        "code": code,
        "url": url,
        "titolo": titolo,
        "testo": testo_pulito,
        "pdf_list": pdf_list,
        "hash": impronta,
        "data_pub": data_pub,
        "data_mod": data_mod,
        "ha_modifica": ha_modifica,
        "rettifica_titolo": bool(re.search(r"rettific|prorog|riapertura|errata corrige|integrazion", titolo, flags=re.IGNORECASE)),
    }


def valuta_bando(titolo, testo, pdf_list, sezione_default):
    tutto = f"{titolo} {testo} {' '.join(p['nome'] for p in pdf_list)}".lower()
    solo_alimentare = bool(re.search(
        r"solo generi alimentari|esclusivamente alimentare|mercato ittico|mercato ortofrutticolo|somministrazione di alimenti e bevande esclusiv",
        tutto,
    ))
    ha_tematica = bool(re.search(
        r"mercatin|fier[ae]|fieristic|hobbist|artigian|opere del proprio ingegno|opere dell'ingegno|pittur|antiquariat|vintage|postegg|stall[io]|vendita occasionale|mostra mercato|espositor",
        tutto,
    ))

    if not ha_tematica or solo_alimentare:
        return {"pertinente": False, "tipo": "Scartato", "zona": sezione_default, "scadenza": "Non indicata", "sintesi": ""}

    tipo = "Nuovo Bando o Avviso"
    if re.search(r"graduatori|ammessi|esit[io]|assegnatari|approvazione elenc", tutto):
        tipo = "Graduatoria o Esiti"
    elif re.search(r"prorog|riapertura|differimento|rettifica|integrazione|errata corrige", tutto):
        tipo = "Proroga o Rettifica"
    elif "manifestazione di interesse" in tutto:
        tipo = "Manifestazione di Interesse"

    zona = sezione_default
    m_mun = re.search(r"municipalit[\xe0a]\s*(?:n\.?\s*)?([1-9]0?|[ivx]{1,4})", f"{titolo} {testo[:800]}", flags=re.IGNORECASE)
    if m_mun:
        zona = f"Municipalita {m_mun.group(1).upper()}"

    scadenza = "Verifica nel bando"
    m_scad = re.search(r"(?:scadenza|entro le ore|entro il giorno|entro il)[^.\n]{4,90}", testo, flags=re.IGNORECASE)
    if m_scad:
        scadenza = m_scad.group(0).strip()

    sintesi = re.sub(r"\s+", " ", testo[:240]).strip() + "..."
    return {"pertinente": True, "tipo": tipo, "zona": zona, "scadenza": scadenza, "sintesi": sintesi}


def invia_telegram(token, chat_id, testo_html):
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
    payload = {
        "chat_id": str(chat_id).strip(),
        "text": testo_html[:4000],
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return 200 <= (resp.getcode() or 200) < 300
    except Exception as e:
        print(f"Errore invio Telegram {e}")
        return False


def formatta_notifica_nuovo(rec):
    righe = [
        f"<b>{unescape(rec['tipo'])}</b>",
        f"<b>Ente</b> Napoli (NA) {rec['sezione']}",
        "",
        f"<b>{unescape(rec['titolo'])}</b>",
        "",
        f"<b>Pubblicazione</b> {rec['dataPubblicazione']}",
        f"<b>Rilevato dal bot</b> {rec['dataRilevamento']}",
        f"<b>Ultima modifica o rettifica</b> {rec['ultimaModifica']}",
        f"<b>Totale modifiche o rettifiche</b> {rec['numModifiche']}",
    ]
    if rec.get("cronologiaModifiche"):
        righe.append("")
        righe.append("<b>Cronologia modifiche e rettifiche</b>")
        for voce in rec["cronologiaModifiche"].split(" || "):
            righe.append(voce)
    if rec.get("scadenza"):
        righe.append("")
        righe.append(f"<b>Scadenza</b> {rec['scadenza']}")
    if rec.get("sintesi"):
        righe.append("")
        righe.append(rec["sintesi"])
    if rec.get("pdfList"):
        righe.append("")
        righe.append(f"<b>Allegati PDF rilevati ({len(rec['pdfList'])})</b>")
        for p in rec["pdfList"][:5]:
            righe.append(f"\u2022 {p['nome']}")
    righe.append("")
    righe.append(f'<a href="{rec["url"]}">Apri la pagina ufficiale del bando</a>')
    return "\n".join(righe)


def formatta_notifica_aggiornamento(rec, motivo):
    righe = [
        "<b>MODIFICA O RETTIFICA SU BANDO SEGUITO</b>",
        f"<b>Ente</b> Napoli (NA) {rec['sezione']}",
        "",
        f"<b>{unescape(rec['titolo'])}</b>",
        "",
        f"<b>Pubblicazione originale</b> {rec['dataPubblicazione']}",
        f"<b>Ultima modifica o rettifica</b> {rec['ultimaModifica']}",
        f"<b>Totale modifiche o rettifiche</b> {rec['numModifiche']}",
        f"<b>Novita rilevata adesso</b> {motivo}",
    ]
    if rec.get("cronologiaModifiche"):
        righe.append("")
        righe.append("<b>Cronologia completa modifiche e rettifiche</b>")
        for voce in rec["cronologiaModifiche"].split(" || "):
            righe.append(voce)
    righe.append("")
    righe.append(f'<a href="{rec["url"]}">Apri la pagina aggiornata</a>')
    return "\n".join(righe)


def carica_stato():
    if os.path.exists("bandi.json"):
        try:
            with open("bandi.json", "r", encoding="utf-8") as f:
                dati = json.load(f)
                if isinstance(dati, dict) and isinstance(dati.get("bandi"), list):
                    return dati
        except Exception as e:
            print(f"Errore lettura bandi.json {e}")
    return {
        "ok": True,
        "generatoIl": formatta_dt(adesso_roma()),
        "ultimoControlloSistema": "",
        "totale": 0,
        "bandi": [],
    }


def salva_stato(stato):
    stato["generatoIl"] = formatta_dt(adesso_roma())
    stato["totale"] = len(stato.get("bandi", []))
    with open("bandi.json", "w", encoding="utf-8") as f:
        json.dump(stato, f, ensure_ascii=False, indent=2)


def esegui_paracadute_gnews(stato, visti_url, visti_titoli, token, chat_id):
    nuovi_trovati = 0
    ok, _, xml_body, _ = scarica_url(URL_PARACADUTE_GNEWS, usa_browser=False)
    if not ok or not xml_body:
        return 0
    items = estrai_notizie_rss(xml_body, URL_PARACADUTE_GNEWS)
    for item in items:
        titolo_pulito = re.sub(r"\s*[\|\u2013\u2014]\s*Comune di Napoli.*$", "", item["titolo"], flags=re.IGNORECASE).strip()
        url_norm = normalizza_url(item["url"])
        chiave_tit = normalizza_titolo_chiave(titolo_pulito)
        if not url_norm or url_norm in visti_url or (chiave_tit and chiave_tit in visti_titoli):
            continue
        if not supera_pre_filtro(titolo_pulito, url_norm):
            continue
        val = valuta_bando(titolo_pulito, item.get("descrizione_rss") or titolo_pulito, [], "Paracadute Google News")
        if not val["pertinente"]:
            continue
        ora_str = formatta_dt(adesso_roma())
        rettifica = bool(re.search(r"rettific|prorog|riapertura|errata corrige|integrazion", titolo_pulito, flags=re.IGNORECASE))
        data_pub = item.get("data_rss") or f"Rilevato il {ora_str}"
        rec = {
            "dataRilevamento": ora_str,
            "provincia": "NA",
            "comune": "Napoli",
            "sezione": val["zona"],
            "titolo": titolo_pulito,
            "url": url_norm,
            "tipo": val["tipo"],
            "scadenza": val["scadenza"],
            "sintesi": val["sintesi"],
            "numPdf": 0,
            "elencoPdf": "",
            "pdfList": [],
            "hash": md5_testo(titolo_pulito + "||" + (item.get("descrizione_rss") or titolo_pulito)),
            "stato": "NUOVO (GNEWS)",
            "dataPubblicazione": data_pub,
            "ultimaModifica": data_pub if rettifica else "Nessuna modifica rilevata",
            "numModifiche": 1 if rettifica else 0,
            "cronologiaModifiche": f"1) {data_pub} - Avviso pubblicato come rettifica, proroga o integrazione" if rettifica else "",
        }
        stato["bandi"].insert(0, rec)
        visti_url.add(url_norm)
        if chiave_tit:
            visti_titoli.add(chiave_tit)
        nuovi_trovati += 1
        invia_telegram(token, chat_id, formatta_notifica_nuovo(rec))
        time.sleep(0.5)
    return nuovi_trovati


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    stato = carica_stato()
    bandi = stato.get("bandi", [])
    indice_per_url = {}
    visti_url = set()
    visti_titoli = set()

    for idx, b in enumerate(bandi):
        u = normalizza_url(b.get("url", ""))
        t = normalizza_titolo_chiave(b.get("titolo", ""))
        if u:
            indice_per_url[u] = idx
            visti_url.add(u)
        if t:
            visti_titoli.add(t)

    sorgenti_lette = 0
    nuovi_pertinenti = 0
    aggiornamenti = 0
    errori = 0
    gnews_gia_usato = False

    for idx_sorg, (sezione, url_sorg, _) in enumerate(SORGENTI_NAPOLI):
        if idx_sorg > 0:
            pausa_cortesia()

        ok, code, html, _ = scarica_con_tentativi(url_sorg)
        if not ok:
            errori += 1
            print(f"Impossibile leggere {sezione} HTTP {code}")
            if code in (403, 429) and not gnews_gia_usato:
                gnews_gia_usato = True
                nuovi_g = esegui_paracadute_gnews(stato, visti_url, visti_titoli, token, chat_id)
                nuovi_pertinenti += nuovi_g
            continue

        sorgenti_lette += 1
        candidati = estrai_notizie_html(html, url_sorg)

        for item in candidati:
            url_norm = normalizza_url(item["url"])
            chiave_tit = normalizza_titolo_chiave(item["titolo"])
            if not url_norm or url_norm in visti_url or (chiave_tit and chiave_tit in visti_titoli):
                continue
            if not supera_pre_filtro(item["titolo"], url_norm):
                continue

            pausa_cortesia()
            det = analizza_dettaglio(url_norm, item["titolo"])
            if not det["ok"]:
                errori += 1
                continue

            chiave_reale = normalizza_titolo_chiave(det["titolo"])
            if chiave_reale and chiave_reale in visti_titoli:
                continue

            val = valuta_bando(det["titolo"], det["testo"], det["pdf_list"], sezione)
            if not val["pertinente"]:
                continue

            ora_str = formatta_dt(adesso_roma())
            data_pub = det["data_pub"] or f"Non indicata dal sito (rilevato il {ora_str})"
            num_mod = 0
            ultima_mod = "Nessuna modifica rilevata"
            cronologia = ""

            if det["ha_modifica"] and det["data_mod"]:
                num_mod = 1
                ultima_mod = det["data_mod"]
                cronologia = f"1) {det['data_mod']} - Aggiornamento o rettifica gia segnalata sul sito"
            elif det["rettifica_titolo"]:
                num_mod = 1
                ultima_mod = det["data_mod"] or det["data_pub"] or ora_str
                cronologia = f"1) {ultima_mod} - Avviso pubblicato come rettifica, proroga o integrazione"

            rec = {
                "dataRilevamento": ora_str,
                "provincia": "NA",
                "comune": "Napoli",
                "sezione": val["zona"],
                "titolo": det["titolo"],
                "url": url_norm,
                "tipo": val["tipo"],
                "scadenza": val["scadenza"],
                "sintesi": val["sintesi"],
                "numPdf": len(det["pdf_list"]),
                "elencoPdf": " | ".join(p["nome"] for p in det["pdf_list"]),
                "pdfList": det["pdf_list"],
                "hash": det["hash"],
                "stato": "NUOVO",
                "dataPubblicazione": data_pub,
                "ultimaModifica": ultima_mod,
                "numModifiche": num_mod,
                "cronologiaModifiche": cronologia,
            }

            stato["bandi"].insert(0, rec)
            visti_url.add(url_norm)
            if chiave_tit:
                visti_titoli.add(chiave_tit)
            if chiave_reale:
                visti_titoli.add(chiave_reale)

            nuovi_pertinenti += 1
            invia_telegram(token, chat_id, formatta_notifica_nuovo(rec))
            time.sleep(0.5)

    # Ricontrolla fino a 6 bandi diretti gia salvati per rilevare modifiche, rettifiche o nuovi PDF
    ricontrollati = 0
    for b in stato["bandi"]:
        if ricontrollati >= 6:
            break
        u = normalizza_url(b.get("url", ""))
        if not u or "news.google.com" in u:
            continue
        ricontrollati += 1
        pausa_cortesia()
        det_att = analizza_dettaglio(u, b.get("titolo", ""))
        if not det_att["ok"]:
            continue

        ora_str = formatta_dt(adesso_roma())
        if not b.get("dataPubblicazione"):
            b["dataPubblicazione"] = det_att["data_pub"] or f"Rilevato il {b.get('dataRilevamento') or ora_str}"

        vecchi_pdf = {p.get("nome") for p in b.get("pdfList", []) if p.get("nome")}
        nuovi_pdf = [p for p in det_att["pdf_list"] if p["nome"] not in vecchi_pdf]
        hash_cambiato = det_att["hash"] != b.get("hash", "")
        data_mod_nuova = bool(
            det_att["data_mod"]
            and det_att["data_mod"] != b.get("ultimaModifica", "")
            and det_att["data_mod"] != b.get("dataPubblicazione", "")
            and det_att["ha_modifica"]
        )

        if nuovi_pdf or hash_cambiato or data_mod_nuova:
            aggiornamenti += 1
            num_mod = int(b.get("numModifiche") or 0) + 1
            if nuovi_pdf:
                nomi_n = ", ".join(p["nome"] for p in nuovi_pdf[:3])
                motivo = f"Nuovi allegati PDF ({nomi_n})"
            elif data_mod_nuova and not hash_cambiato:
                motivo = "Data di modifica aggiornata sul sito"
            else:
                motivo = "Modifica o rettifica del testo nella pagina"

            ts_mod = (
                f"{det_att['data_mod']} (rilevata il {ora_str})"
                if (det_att["data_mod"] and det_att["data_mod"] != b.get("ultimaModifica", ""))
                else ora_str
            )
            voce = f"{num_mod}) {ts_mod} - {motivo}"
            cron_prec = b.get("cronologiaModifiche", "")
            b["numPdf"] = len(det_att["pdf_list"])
            b["elencoPdf"] = " | ".join(p["nome"] for p in det_att["pdf_list"])
            b["pdfList"] = det_att["pdf_list"]
            b["hash"] = det_att["hash"]
            b["ultimaModifica"] = ts_mod
            b["numModifiche"] = num_mod
            b["cronologiaModifiche"] = f"{cron_prec} || {voce}" if cron_prec else voce
            b["stato"] = f"MODIFICATO ({num_mod})"

            invia_telegram(token, chat_id, formatta_notifica_aggiornamento(b, motivo))
            time.sleep(0.5)

    stato["ultimoControlloSistema"] = formatta_dt(adesso_roma())
    salva_stato(stato)

    riepilogo = (
        f"<b>Controllo GitHub completato</b> ({stato['ultimoControlloSistema']})\n\n"
        f"<b>Sorgenti lette</b> {sorgenti_lette}\n"
        f"<b>Nuovi bandi pertinenti</b> {nuovi_pertinenti}\n"
        f"<b>Modifiche o rettifiche rilevate</b> {aggiornamenti}\n"
        f"<b>Errori o blocchi</b> {errori}"
    )
    invia_telegram(token, chat_id, riepilogo)
    print(riepilogo)


if __name__ == "__main__":
    main()
