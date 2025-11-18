from flask import Flask, render_template_string, request 
import spacy
import re

app = Flask(__name__)
nlp = spacy.load("pt_core_news_lg")

def add_span_if_free(spans, start, end, label):
    for s, e, _ in spans:
        if not (end <= s or start >= e):  # overlap
            return False
    spans.append((start, end, label))
    return True

def find_regex_spans(text):
    spans = []
    # CPF
    for m in re.finditer(r"\b\d{3}\.?\d{3}\.?\d{3}\-?\d{2}\b", text):
        add_span_if_free(spans, m.start(), m.end(), "[CPF]")
    # RG
    for m in re.finditer(r"\b\d{1,2}\.?\d{3}\.?\d{3}\-?[0-9Xx]\b", text):
        add_span_if_free(spans, m.start(), m.end(), "[RG]")
    # CNPJ
    for m in re.finditer(r"\b\d{2}\.?\d{3}\.?\d{3}\/?\d{4}\-?\d{2}\b", text):
        add_span_if_free(spans, m.start(), m.end(), "[CNPJ]")
    # Telefones
    for m in re.finditer(
        r"(?:(?:\+?55[\s\-]?)?(?:\(?\d{2}\)?[\s\-]?)?)?(?:9\d{3}|\d{4})[\s\-]?\d{4}\b", text):
        add_span_if_free(spans, m.start(), m.end(), "[TELEFONE]")
    # Emails
    for m in re.finditer(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text):
        add_span_if_free(spans, m.start(), m.end(), "[EMAIL]")
    # Datas numéricas
    for m in re.finditer(r"\b\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}\b", text):
        add_span_if_free(spans, m.start(), m.end(), "[DATA]")
    # Datas por extenso
    meses = ("janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro")
    for m in re.finditer(rf"\b\d{{1,2}}\s+de\s+(?:{meses})(?:\s+de\s+\d{{4}})?\b", text, flags=re.IGNORECASE):
        add_span_if_free(spans, m.start(), m.end(), "[DATA]")
    # Endereços
    for m in re.finditer(
        r"\b(?:Rua|R\.|Avenida|Av\.|Av|Travessa|Alameda|Rodovia|Estrada)\s+[A-ZÁÉÍÓÚÃÕÂÊÔ0-9a-záéíóúãõâêô\.\- ]+(?:,\s*\d+)?\b",
        text, flags=re.IGNORECASE):
        add_span_if_free(spans, m.start(), m.end(), "[ENDEREÇO]")
    # Nome pessoal
    for m in re.finditer(
        r"\b([A-ZÁÉÍÓÚÃÕÂÊÔ][a-záéíóúãõâêô]+(?:\s+(?:da|de|do|dos|das))?\s+[A-ZÁÉÍÓÚÃÕÂÊÔ][a-záéíóúãõâêô]+)\b",
        text):
        add_span_if_free(spans, m.start(1), m.end(1), "[NOME]")
    # Corporação
    for m in re.finditer(
        r"\b(?:Empresa|Companhia|Corporação|Banco|Prefeitura|Governo|Ministério|Universidade|Faculdade|Escola|Hospital|Instituto|Associação|Fundação|Sindicato|Cooperativa|Conselho|Assembleia|Câmara|ONG|Organização)\s+[A-ZÁÉÍÓÚÃÕÂÊÔ0-9a-záéíóúãõâêô\.\- ]+",
        text, flags=re.IGNORECASE):
        add_span_if_free(spans, m.start(), m.end(), "[ORG]")
    # IPv4
    for m in re.finditer(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d{1,2})\.){3}(?:25[0-5]|2[0-4]\d|1?\d{1,2})\b", text):
        add_span_if_free(spans, m.start(), m.end(), "[IP]")
    # IPv6
    for m in re.finditer(r"\b([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}\b", text):
        add_span_if_free(spans, m.start(), m.end(), "[IP]")

    # ==== NOVO BLOCO: Dados Bancários ====
    # 1) Detecção de "termina em/termina com 4321" (últimos 3-4 dígitos de cartão)
    for m in re.finditer(r"\b(?:termina(?:m)?\s+(?:em|com))\s+(\d{3,4})\b", text, flags=re.IGNORECASE):
        # marca apenas os dígitos (grupo 1)
        start, end = m.start(1), m.end(1)
        add_span_if_free(spans, start, end, "[DADO_BANCARIO]")

    # 2) Cartão completo (13 a 19 dígitos, com ou sem espaços/hífens) - detecta números longos
    for m in re.finditer(r"\b(?:\d[ -]*?){13,19}\b", text):
        add_span_if_free(spans, m.start(), m.end(), "[DADO_BANCARIO]")

    # 3) Agência / Conta com qualificadores (ex.: "Conta Corrente 12345-6", "Conta Poupança 1234")
    # permite um qualificativo comum entre "Conta" e o número (Corrente, Poupança, cc, corr.)
    for m in re.finditer(
        r"\bAg[eê]ncia[:\s]*\d{1,6}\b"  # Agência 0123
        r"|\bConta(?:\s+(?:Corrente|Poupança|Poup|Corrente\.|Corr\.|cc|corr))?[:\s\-]*\d{1,12}[-]?\d?\b",
        text, flags=re.IGNORECASE):
        add_span_if_free(spans, m.start(), m.end(), "[DADO_BANCARIO]")
    # PIX UUID
    for m in re.finditer(r"\b[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b", text):
        add_span_if_free(spans, m.start(), m.end(), "[DADO_BANCARIO]")
    # PIX por telefone
    for m in re.finditer(r"\b\+?55\s?\(?\d{2}\)?\s?\d{4,5}[- ]?\d{4}\b", text):
        add_span_if_free(spans, m.start(), m.end(), "[DADO_BANCARIO]")
    # PIX por e-mail (já cobre alguns e-mails em geral, mas reforçamos aqui)
    for m in re.finditer(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text):
        add_span_if_free(spans, m.start(), m.end(), "[DADO_BANCARIO]")

    return spans

def anonimizar_texto(texto, lei):
    doc = nlp(texto)
    spans = []
    for ent in doc.ents:
        label = None
        if ent.label_ == "PERSON":
            label = "[NOME]"
        elif ent.label_ in ("ORG",):
            label = "[ORG]"
        elif ent.label_ in ("GPE", "LOC"):
            label = "[LOC]"
        elif ent.label_ == "DATE":
            label = "[DATA]"
        if label:
            add_span_if_free(spans, ent.start_char, ent.end_char, label)

    regex_spans = find_regex_spans(texto)
    for s, e, lab in regex_spans:
        add_span_if_free(spans, s, e, lab)

    spans_sorted = sorted(spans, key=lambda x: x[0], reverse=True)

    if lei == 'lgpd':
        explicacoes = {
            "[NOME]": "Identifica diretamente uma pessoa natural — dado pessoal (art. 5º, I, LGPD).",
            "[CPF]": "Número de identificação individual — dado pessoal sensível e identificador único.",
            "[RG]": "Documento de identificação — dado pessoal sensível (identificador oficial).",
            "[CNPJ]": "Identifica pessoa jurídica — não é dado pessoal, exceto se vinculado a um empresário individual.",
            "[TELEFONE]": "Permite contato direto com o titular — dado pessoal (informação de contato).",
            "[EMAIL]": "Identifica e possibilita contato digital com o titular — dado pessoal (identificador digital).",
            "[DATA]": "Pode revelar idade ou informações sobre o titular — dado pessoal (informação biográfica).",
            "[ENDEREÇO]": "Permite localização física do titular — dado pessoal (dado de localização).",
            "[ORG]": "Identifica uma organização associada ao titular — dado pessoal indireto.",
            "[LOC]": "Revela local ou região associada ao titular — dado pessoal indireto.",
            "[IP]": "Identifica dispositivos e localização aproximada — dado pessoal.",
            "[DADO_BANCARIO]": "Inclui informações financeiras como conta, agência, cartão ou chave PIX — dado pessoal de alto risco (não sensível pela LGPD, mas requer proteção reforçada).",
        }
    else:
        explicacoes = {
        "[NOME]": "Personal data: identifica diretamente uma pessoa natural (GDPR Art. 4(1)).",
        "[CPF]": "Identificador único equivalente a 'national identification number'. Sob a GDPR, é dado pessoal de alto risco que exige proteção reforçada.",
        "[RG]": "Identificador oficial nacional — considerado 'unique identifier' pela GDPR, exigindo medidas adicionais (GDPR Art. 87).",
        "[CNPJ]": "Identifica pessoa jurídica — não é personal data sob a GDPR, exceto se associado a empresário individual (identifiable natural person).",
        "[TELEFONE]": "Informação de contato que identifica ou pode identificar um titular — personal data (GDPR Art. 4(1)).",
        "[EMAIL]": "Identificador digital direto — personal data sob a GDPR, mesmo quando corporativo.",
        "[DATA]": "Informação biográfica que pode identificar o titular ou revelar idade — personal data.",
        "[ENDEREÇO]": "Localização física que identifica ou pode identificar uma pessoa — personal data, com risco aumentado (Recital 30).",
        "[ORG]": "Associação organizacional pode identificar indiretamente o titular — personal data caso possibilite identificação.",
        "[LOC]": "Dado de geolocalização ou referência territorial — personal data (Recital 30).",
        "[IP]": "Endereço IP é personal data sob a GDPR (Recital 30) pois identifica dispositivos do titular.",
        "[DADO_BANCARIO]": "Financial personal data — não é 'special category', mas possui alto risco e exige salvaguardas reforçadas (GDPR Art. 32).",
        }

    texto_anon = texto
    for start, end, label in spans_sorted:
        explicacao = explicacoes.get(label, "Dado pessoal sensível detectado.")
        label_classes = {
            "[NOME]": "anon nome",
            "[CPF]": "anon cpf",
            "[RG]": "anon rg",
            "[CNPJ]": "anon cnpj",
            "[TELEFONE]": "anon telefone",
            "[EMAIL]": "anon email",
            "[DATA]": "anon data",
            "[ENDEREÇO]": "anon endereco",
            "[ORG]": "anon org",
            "[LOC]": "anon loc",
            "[IP]": "anon ip",
            "[DADO_BANCARIO]": "anon bancario",
        }

        css_class = label_classes.get(label, "anon")
        popup = f'<span class="{css_class}" title="{explicacao}">{label}</span>'
        texto_anon = texto_anon[:start] + popup + texto_anon[end:]

    return texto_anon
