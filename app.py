import streamlit as st


# -----------------------------
# Вспомогательные функции
# -----------------------------
def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    """Ограничение значения диапазоном [min_value, max_value]."""
    return max(min_value, min(value, max_value))


def normalize_direct(x: float, x_min: float, x_max: float) -> float:
    """
    Нормализация параметра, при которой рост значения увеличивает риск.
    Например: ВГД, возраст, CDR.
    """
    if x_max == x_min:
        return 0.0
    return clamp((x - x_min) / (x_max - x_min))


def normalize_inverse(x: float, x_min: float, x_max: float) -> float:
    """
    Нормализация параметра, при которой уменьшение значения увеличивает риск.
    Например: толщина роговицы (тонкая роговица -> выше риск).
    """
    if x_max == x_min:
        return 0.0
    return clamp((x_max - x) / (x_max - x_min))


def correct_iop_by_cct(iop: float, cct: float, k: float = 0.02, cct_ref: float = 540.0) -> float:
    """
    Упрощённая коррекция ВГД по толщине роговицы.
    IOPcorr = IOP + k * (540 - CCT)

    k = 0.02 мм рт. ст. на 1 мкм отклонения от 540 мкм
    Это демонстрационная модель для прототипа.
    """
    return iop + k * (cct_ref - cct)


def risk_label(risk_index: float) -> str:
    """Интерпретация индекса риска."""
    if risk_index < 0.3:
        return "Низкий риск"
    elif risk_index < 0.6:
        return "Умеренный риск"
    return "Высокий риск"


# -----------------------------
# Расчёт моделей
# -----------------------------
def calculate_base_model(iop: float, cct: float, age: float) -> dict:
    """
    Базовая модель:
    - коррекция ВГД по CCT
    - нормализация параметров
    - расчёт интегрального индекса риска

    Веса заданы экспертно:
    ВГД = 0.5
    CCT = 0.25
    Возраст = 0.25
    """
    iop_corr = correct_iop_by_cct(iop, cct)

    iop_norm = normalize_direct(iop_corr, 10, 30)
    cct_norm = normalize_inverse(cct, 480, 620)
    age_norm = normalize_direct(age, 20, 80)

    risk = 0.5 * iop_norm + 0.25 * cct_norm + 0.25 * age_norm
    risk = clamp(risk)

    return {
        "iop_corr": round(iop_corr, 2),
        "iop_norm": round(iop_norm, 3),
        "cct_norm": round(cct_norm, 3),
        "age_norm": round(age_norm, 3),
        "risk": round(risk, 3),
        "label": risk_label(risk),
    }


def calculate_extended_model(iop: float, cct: float, age: float, cdr: float) -> dict:
    """
    Расширенная модель:
    - базовая часть
    - добавляется параметр CDR

    Веса:
    ВГД = 0.4
    CCT = 0.2
    Возраст = 0.2
    CDR = 0.2
    """
    iop_corr = correct_iop_by_cct(iop, cct)

    iop_norm = normalize_direct(iop_corr, 10, 30)
    cct_norm = normalize_inverse(cct, 480, 620)
    age_norm = normalize_direct(age, 20, 80)
    cdr_norm = normalize_direct(cdr, 0.0, 1.0)

    risk = (
        0.4 * iop_norm
        + 0.2 * cct_norm
        + 0.2 * age_norm
        + 0.2 * cdr_norm
    )
    risk = clamp(risk)

    return {
        "iop_corr": round(iop_corr, 2),
        "iop_norm": round(iop_norm, 3),
        "cct_norm": round(cct_norm, 3),
        "age_norm": round(age_norm, 3),
        "cdr_norm": round(cdr_norm, 3),
        "risk": round(risk, 3),
        "label": risk_label(risk),
    }


# -----------------------------
# Интерфейс Streamlit
# -----------------------------
st.set_page_config(
    page_title="Оценка риска глаукомы",
    page_icon="👁️",
    layout="centered",
)

st.title("👁️ Прототип цифровой системы оценки риска глаукомы")
st.write(
    """
    Демонстрационный прототип для оценки риска глаукомных изменений
    на основе внутриглазного давления (ВГД), центральной толщины роговицы (CCT),
    возраста пациента и, при необходимости, параметра cup-to-disc ratio (CDR).
    """
)

st.info(
    "Важно: это учебный прототип для визуализации алгоритма. "
    "Он не является медицинским изделием и не предназначен для постановки диагноза."
)

st.subheader("Входные данные")

col1, col2 = st.columns(2)

with col1:
    iop = st.number_input(
        "Внутриглазное давление (мм рт. ст.)",
        min_value=5.0,
        max_value=50.0,
        value=21.0,
        step=0.5,
    )
    cct = st.number_input(
        "Центральная толщина роговицы CCT (мкм)",
        min_value=400.0,
        max_value=700.0,
        value=540.0,
        step=1.0,
    )

with col2:
    age = st.number_input(
        "Возраст пациента (лет)",
        min_value=10,
        max_value=100,
        value=45,
        step=1,
    )
    use_cdr = st.checkbox("Использовать расширенную модель с CDR", value=True)

cdr = None
if use_cdr:
    cdr = st.slider(
        "Cup-to-disc ratio (CDR)",
        min_value=0.0,
        max_value=1.0,
        value=0.4,
        step=0.01,
    )

st.markdown("---")

if st.button("Рассчитать риск"):
    base_result = calculate_base_model(iop, cct, age)

    st.subheader("Результаты базовой модели")
    st.metric("Скорректированное ВГД", f"{base_result['iop_corr']} мм рт. ст.")
    st.metric("Индекс риска R₁", base_result["risk"])
    st.progress(base_result["risk"])
    st.write(f"**Интерпретация:** {base_result['label']}")

    with st.expander("Показать детали базовой модели"):
        st.write(f"Нормализованное ВГД: **{base_result['iop_norm']}**")
        st.write(f"Нормализованная CCT: **{base_result['cct_norm']}**")
        st.write(f"Нормализованный возраст: **{base_result['age_norm']}**")

    if use_cdr and cdr is not None:
        ext_result = calculate_extended_model(iop, cct, age, cdr)

        st.markdown("---")
        st.subheader("Результаты расширенной модели")
        st.metric("Скорректированное ВГД", f"{ext_result['iop_corr']} мм рт. ст.")
        st.metric("Индекс риска R₂", ext_result["risk"])
        st.progress(ext_result["risk"])
        st.write(f"**Интерпретация:** {ext_result['label']}")

        with st.expander("Показать детали расширенной модели"):
            st.write(f"Нормализованное ВГД: **{ext_result['iop_norm']}**")
            st.write(f"Нормализованная CCT: **{ext_result['cct_norm']}**")
            st.write(f"Нормализованный возраст: **{ext_result['age_norm']}**")
            st.write(f"Нормализованный CDR: **{ext_result['cdr_norm']}**")

    st.markdown("---")
    st.caption(
        "Шкала интерпретации: 0–0.3 — низкий риск; 0.3–0.6 — умеренный риск; выше 0.6 — высокий риск."
    )
