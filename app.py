import streamlit as st
import pandas as pd
from pathlib import Path
from supabase import create_client

st.set_page_config(
    page_title="USGEP Branş Yönlendirme",
    layout="wide"
)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def sporculari_getir():
    data = supabase.table("sporcular").select("*").order("id").execute()
    return pd.DataFrame(data.data)


def testleri_getir():
    data = supabase.table("testler").select("*").order("id").execute()
    return pd.DataFrame(data.data)


with st.sidebar:
    logo_yolu = Path(__file__).parent / "logo.png"

    if logo_yolu.exists():
        st.image(str(logo_yolu), width=180)

    st.title("USGEP Menü")

    sayfa = st.radio(
        "Sayfa Seç",
        [
            "🏠 Ana Sayfa",
            "🧒 Sporcu Kayıt",
            "📋 Test Veri Girişi",
            "📊 Sonuçlar",
            "📈 Dashboard"
        ]
    )


if sayfa == "🏠 Ana Sayfa":

    st.title("USGEP Branş Yönlendirme Sistemi")

    st.markdown("""
    ### Sistem Durumu

    ✅ Online erişim aktif  
    ✅ Tablet erişimi aktif  
    ✅ Streamlit Cloud yayında  
    ✅ Supabase veritabanı bağlı  

    ---
    """)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Tablet", "6")

    with col2:
        st.metric("Branş", "5")

    with col3:
        st.metric("Test Alanı", "17")


elif sayfa == "🧒 Sporcu Kayıt":

    st.title("Sporcu Kayıt")

    with st.form("sporcu_form"):
        ad = st.text_input("Ad Soyad")
        yas = st.number_input("Yaş", 5, 18)
        cinsiyet = st.selectbox("Cinsiyet", ["ERKEK", "KIZ"])
        ilce = st.text_input("İlçe")

        submit = st.form_submit_button("Kaydet")

        if submit:
            if not ad.strip():
                st.warning("Ad soyad boş bırakılamaz.")
            else:
                supabase.table("sporcular").insert({
                    "ad_soyad": ad.strip(),
                    "yas": int(yas),
                    "cinsiyet": cinsiyet,
                    "ilce": ilce.strip()
                }).execute()

                st.success("Sporcu Supabase veritabanına kaydedildi.")


elif sayfa == "📋 Test Veri Girişi":

    st.title("Test Veri Girişi")

    sporcular = sporculari_getir()

    if sporcular.empty:
        st.warning("Önce sporcu kaydı oluşturun.")
    else:
        sporcular["secim"] = sporcular["id"].astype(str) + " - " + sporcular["ad_soyad"]

        secili = st.selectbox("Sporcu Seç", sporcular["secim"])

        sporcu_id = int(secili.split(" - ")[0])

        st.subheader("Testler")

        boy = st.number_input("Boy", min_value=0.0, step=0.1)
        kilo = st.number_input("Kilo", min_value=0.0, step=0.1)
        sprint20 = st.number_input("20m Sprint", min_value=0.0, step=0.01)
        dikey_sicrama = st.number_input("Dikey Sıçrama", min_value=0.0, step=0.1)

        if st.button("Testleri Kaydet"):
            supabase.table("testler").insert({
                "sporcu_id": sporcu_id,
                "boy": float(boy),
                "kilo": float(kilo),
                "sprint20": float(sprint20),
                "dikey_sicrama": float(dikey_sicrama)
            }).execute()

            st.success("Test verileri Supabase veritabanına kaydedildi.")


elif sayfa == "📊 Sonuçlar":

    st.title("Sonuçlar")

    sporcular = sporculari_getir()
    testler = testleri_getir()

    if testler.empty:
        st.info("Henüz test sonucu bulunmuyor.")
    else:
        if not sporcular.empty:
            sonuc = testler.merge(
                sporcular,
                left_on="sporcu_id",
                right_on="id",
                how="left",
                suffixes=("_test", "_sporcu")
            )
        else:
            sonuc = testler

        st.dataframe(sonuc, use_container_width=True)


elif sayfa == "📈 Dashboard":

    st.title("Dashboard")

    sporcular = sporculari_getir()
    testler = testleri_getir()

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Toplam Sporcu", len(sporcular))

    with col2:
        st.metric("Toplam Test Kaydı", len(testler))

    st.subheader("Sporcu Listesi")
    st.dataframe(sporcular, use_container_width=True)

    st.subheader("Test Listesi")
    st.dataframe(testler, use_container_width=True)
