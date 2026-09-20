import streamlit as st
import requests
import xml.etree.ElementTree as ET
from google import genai

# Настройка страницы
st.set_page_config(page_title="PubMed AI", page_icon="🔬", layout="centered")

# Получение API-ключа Gemini
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error("Пожалуйста, укажите GEMINI_API_KEY в настройках Streamlit Secrets!")
    st.stop()

# Инициализация клиента Gemini
client = genai.Client(api_key=api_key)

def search_pubmed(query, max_results=5):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {"db": "pubmed", "term": query, "retmax": max_results, "retmode": "json"}
    res = requests.get(url, params=params).json()
    return res.get("esearchresult", {}).get("idlist", [])

def fetch_article_details(pmid_list):
    if not pmid_list:
        return []
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {"db": "pubmed", "id": ",".join(pmid_list), "retmode": "xml"}
    res = requests.get(url, params=params)
    root = ET.fromstring(res.content)
    
    articles = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article.find(".//PMID").text
        title_el = article.find(".//ArticleTitle")
        title = title_el.text if title_el is not None else "Без названия"
        abstract_texts = article.findall(".//AbstractText")
        abstract = " ".join([elem.text for elem in abstract_texts if elem.text]) if abstract_texts else "Аннотация отсутствует."
        articles.append({"pmid": pmid, "title": title, "abstract": abstract})
    return articles

def translate_medical_text(text):
    prompt = f"""
    Ты профессиональный медицинский переводчик и научный редактор.
    Переведи следующий текст с английского на русский язык.
    Передай глубокий смысл, используй профессиональную врачебную терминологию, избегай дословного перевода.
    
    Текст:
    {text}
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

st.title("🔬 PubMed AI Переводчик (Gemini)")

query = st.text_input("Введите тему исследования (на английском):", placeholder="e.g. myocarditis treatment")

if st.button("Искать статьи", type="primary"):
    if query:
        with st.spinner("Поиск в PubMed..."):
            pmids = search_pubmed(query)
            st.session_state['articles'] = fetch_article_details(pmids)

if 'articles' in st.session_state:
    for idx, item in enumerate(st.session_state['articles']):
        st.subheader(f"{idx+1}. {item['title']}")
        st.caption(f"PMID: {item['pmid']}")
        
        with st.expander("Оригинал (Abstract)"):
            st.write(item['abstract'])
            
        if st.button(f"🌐 Перевести смыслово", key=f"btn_{item['pmid']}"):
            with st.spinner("Переводим нейросетью Gemini..."):
                trans_title = translate_medical_text(item['title'])
                trans_abstract = translate_medical_text(item['abstract'])
                st.success("Перевод готов:")
                st.markdown(f"**Заголовок:** {trans_title}")
                st.markdown(f"**Аннотация:**\n{trans_abstract}")
        st.divider()
