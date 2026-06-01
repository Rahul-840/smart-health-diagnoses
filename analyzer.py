import json
import re
from typing import Any, Dict, List, Optional, Tuple

# Medical reference ranges used by the app. Lab ranges can differ by age, sex, method, and lab.
NORMAL_RANGES: Dict[str, Dict[str, Any]] = {
    "hemoglobin": {"aliases": ["hemoglobin", "haemoglobin", "hb"], "low": 13.0, "high": 17.0, "unit": "g/dL", "low_risk": "Low hemoglobin can be associated with anemia, tiredness, or weakness.", "high_risk": "High hemoglobin can be associated with dehydration or increased red blood cell concentration."},
    "wbc": {"aliases": ["wbc", "white blood cell", "white blood cells", "tlc", "total leukocyte count", "total leucocyte count"], "low": 4000, "high": 11000, "unit": "/µL", "low_risk": "Low WBC may suggest reduced immune cell count or infection risk.", "high_risk": "High WBC may suggest infection, inflammation, or stress response."},
    "neutrophils": {"aliases": ["neutrophils", "neutrophil"], "low": 40, "high": 80, "unit": "%", "low_risk": "Low neutrophils can reduce bacterial infection-fighting capacity.", "high_risk": "High neutrophils may appear in infection, inflammation, or stress."},
    "lymphocytes": {"aliases": ["lymphocyte", "lymphocytes"], "low": 20, "high": 40, "unit": "%", "low_risk": "Low lymphocytes may reflect reduced immune cell percentage or recent stress/infection.", "high_risk": "High lymphocytes may occur with some infections or immune responses."},
    "eosinophils": {"aliases": ["eosinophil", "eosinophils"], "low": 1, "high": 6, "unit": "%", "low_risk": "Low eosinophils are often not significant alone.", "high_risk": "High eosinophils may be linked with allergy, asthma, or parasitic infection."},
    "monocytes": {"aliases": ["monocyte", "monocytes"], "low": 2, "high": 10, "unit": "%", "low_risk": "Low monocytes should be interpreted with the full CBC and symptoms.", "high_risk": "High monocytes may be seen with infection, inflammation, or recovery after illness."},
    "basophils": {"aliases": ["basophil", "basophils"], "low": 0, "high": 2, "unit": "%", "low_risk": "Low basophils are usually not a concern.", "high_risk": "High basophils may be associated with allergy or inflammation."},
    "rbc": {"aliases": ["total rbc count", "rbc count", "rbc", "red blood cell", "red blood cells"], "low": 4.5, "high": 5.9, "unit": "million/µL", "low_risk": "Low RBC may suggest anemia or blood loss.", "high_risk": "High RBC may suggest dehydration or increased red cell concentration."},
    "platelets": {"aliases": ["platelet count", "platelets", "platelet"], "low": 150000, "high": 450000, "unit": "/µL", "low_risk": "Low platelets may increase bleeding tendency.", "high_risk": "High platelets may be associated with inflammation or clotting tendency."},
    "hematocrit": {"aliases": ["hematocrit value", "hematocrit", "hct"], "low": 40, "high": 50, "unit": "%", "low_risk": "Low hematocrit may occur with anemia or blood loss.", "high_risk": "High hematocrit may occur with dehydration or increased red cell concentration."},
    "mcv": {"aliases": ["mean corpuscular volume", "mcv"], "low": 83, "high": 101, "unit": "fL", "low_risk": "Low MCV may suggest microcytic anemia pattern.", "high_risk": "High MCV may suggest macrocytic anemia pattern."},
    "mchc": {"aliases": ["mean cell haemoglobin con", "mean cell hemoglobin con", "mean corpuscular hemoglobin concentration", "mchc"], "low": 31.5, "high": 34.5, "unit": "%", "low_risk": "Low MCHC may suggest hypochromic anemia pattern.", "high_risk": "High MCHC should be reviewed with the lab report and doctor."},
    "mch": {"aliases": ["mean cell haemoglobin", "mean cell hemoglobin", "mch"], "low": 27, "high": 32, "unit": "pg", "low_risk": "Low MCH may indicate lower hemoglobin content in red blood cells.", "high_risk": "High MCH may be associated with larger red blood cells."},
    "glucose": {"aliases": ["fasting plasma glucose", "fasting sugar", "blood sugar", "glucose", "fbs", "rbs"], "low": 70, "high": 110, "unit": "mg/dL", "low_risk": "Low sugar can cause weakness, sweating, dizziness, or faintness.", "high_risk": "High sugar may suggest diabetes risk or poor sugar control."},
    "hba1c": {"aliases": ["hba1c", "hb a1c", "glycated hemoglobin", "glycosylated hemoglobin"], "low": 0, "high": 5.7, "unit": "%", "low_risk": "Low HbA1c is uncommon and should be interpreted clinically.", "high_risk": "High HbA1c may suggest prediabetes or diabetes risk depending on the level."},
    "cholesterol": {"aliases": ["total cholesterol", "cholesterol"], "low": 0, "high": 200, "unit": "mg/dL", "low_risk": "Very low cholesterol should be reviewed clinically.", "high_risk": "High total cholesterol may increase cardiovascular risk."},
    "ldl": {"aliases": ["ldl cholesterol", "ldl"], "low": 0, "high": 100, "unit": "mg/dL", "low_risk": "Low LDL is usually not a concern unless clinically indicated.", "high_risk": "High LDL may increase cardiovascular risk."},
    "hdl": {"aliases": ["hdl cholesterol", "hdl"], "low": 40, "high": 999, "unit": "mg/dL", "low_risk": "Low HDL may increase heart risk.", "high_risk": "High HDL is usually considered protective."},
    "triglycerides": {"aliases": ["triglycerides", "triglyceride", "tg"], "low": 0, "high": 150, "unit": "mg/dL", "low_risk": "Low triglycerides are usually not a concern alone.", "high_risk": "High triglycerides may increase metabolic and cardiovascular risk."},
    "tsh": {"aliases": ["thyroid stimulating hormone", "tsh"], "low": 0.4, "high": 4.0, "unit": "mIU/L", "low_risk": "Low TSH may suggest hyperthyroid tendency.", "high_risk": "High TSH may suggest hypothyroid tendency."},
    "t3": {"aliases": ["total t3", "t3"], "low": 80, "high": 180, "unit": "ng/dL", "low_risk": "Low T3 should be reviewed with thyroid profile and symptoms.", "high_risk": "High T3 may suggest thyroid overactivity depending on the profile."},
    "t4": {"aliases": ["total t4", "t4"], "low": 4.5, "high": 12.0, "unit": "µg/dL", "low_risk": "Low T4 may suggest thyroid underactivity depending on TSH.", "high_risk": "High T4 may suggest thyroid overactivity depending on TSH."},
    "creatinine": {"aliases": ["serum creatinine", "creatinine"], "low": 0.6, "high": 1.3, "unit": "mg/dL", "low_risk": "Low creatinine may relate to low muscle mass.", "high_risk": "High creatinine may suggest kidney function concern."},
    "urea": {"aliases": ["blood urea", "urea"], "low": 10, "high": 50, "unit": "mg/dL", "low_risk": "Low urea may relate to diet or liver factors.", "high_risk": "High urea may suggest dehydration or kidney-related concern."},
    "sgpt": {"aliases": ["sgpt", "alt"], "low": 0, "high": 45, "unit": "U/L", "low_risk": "Low ALT/SGPT is usually not a concern.", "high_risk": "High ALT/SGPT may suggest liver inflammation or injury."},
    "sgot": {"aliases": ["sgot", "ast"], "low": 0, "high": 40, "unit": "U/L", "low_risk": "Low AST/SGOT is usually not a concern.", "high_risk": "High AST/SGOT may relate to liver, muscle, or heart tissue injury."},
    "bilirubin": {"aliases": ["total bilirubin", "bilirubin"], "low": 0, "high": 1.2, "unit": "mg/dL", "low_risk": "Low bilirubin is usually not a concern.", "high_risk": "High bilirubin may suggest liver, bile duct, or blood breakdown concern."},
    "vitamin d": {"aliases": ["25-oh vitamin d", "vitamin d", "25 hydroxy vitamin d"], "low": 30, "high": 100, "unit": "ng/mL", "low_risk": "Low vitamin D may be linked with bone pain, weakness, or deficiency.", "high_risk": "Very high vitamin D can be harmful and should be reviewed."},
    "vitamin b12": {"aliases": ["vitamin b12", "b12"], "low": 200, "high": 900, "unit": "pg/mL", "low_risk": "Low B12 may cause weakness, numbness, or anemia-like symptoms.", "high_risk": "High B12 should be interpreted with clinical context."},
}

MEDICAL_TERMS: Dict[str, str] = {
    "hemoglobin": "Hemoglobin carries oxygen in the blood.",
    "wbc": "WBC reflects immune activity and infection response.",
    "neutrophils": "Neutrophils are white blood cells that help fight bacterial infections.",
    "lymphocytes": "Lymphocytes are white blood cells related to immune response.",
    "eosinophils": "Eosinophils are often linked with allergy or parasitic response.",
    "monocytes": "Monocytes are involved in infection and inflammation response.",
    "basophils": "Basophils are involved in allergy and inflammation response.",
    "rbc": "RBC carries oxygen through red blood cells.",
    "platelets": "Platelets help blood clot and stop bleeding.",
    "hematocrit": "Hematocrit shows the percentage of blood volume made up by red blood cells.",
    "mcv": "MCV shows the average size of red blood cells.",
    "mch": "MCH shows the average hemoglobin amount in red blood cells.",
    "mchc": "MCHC shows average hemoglobin concentration inside red blood cells.",
    "glucose": "Glucose shows blood sugar level.",
    "hba1c": "HbA1c shows average blood sugar control over the last 2 to 3 months.",
    "cholesterol": "Total cholesterol is related to heart and blood vessel health.",
    "ldl": "LDL is often called bad cholesterol because high levels increase heart risk.",
    "hdl": "HDL is often called good cholesterol and helps protect heart health.",
    "triglycerides": "Triglycerides are blood fats related to metabolic and heart health.",
    "tsh": "TSH shows thyroid gland activity.",
    "t3": "T3 is a thyroid hormone involved in metabolism.",
    "t4": "T4 is a thyroid hormone that helps regulate metabolism.",
    "creatinine": "Creatinine helps estimate kidney function.",
    "urea": "Urea is related to protein metabolism and kidney function.",
    "sgpt": "SGPT/ALT is a liver enzyme.",
    "sgot": "SGOT/AST is an enzyme related to liver, muscle, and heart tissues.",
    "bilirubin": "Bilirubin is related to liver and bile processing.",
    "vitamin d": "Vitamin D supports bones, muscles, and immunity.",
    "vitamin b12": "Vitamin B12 supports nerves, blood cell formation, and energy.",
}

DISCLAIMER = "This tool helps explain reports in simple language. It does not replace a certified doctor."


def extract_pdf_text(uploaded_file) -> str:
    """Extract text from a PDF using pdfplumber first and PyPDF2 as fallback."""
    errors: List[str] = []
    try:
        import pdfplumber
        uploaded_file.seek(0)
        pages: List[str] = []
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                txt = page.extract_text() or ""
                if txt.strip():
                    pages.append(txt)
        text = "\n".join(pages).strip()
        if text:
            return text
        errors.append("pdfplumber returned empty text")
    except Exception as exc:
        errors.append(f"pdfplumber: {exc}")

    try:
        import PyPDF2
        uploaded_file.seek(0)
        reader = PyPDF2.PdfReader(uploaded_file)
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        if text:
            return text
        errors.append("PyPDF2 returned empty text")
    except Exception as exc:
        errors.append(f"PyPDF2: {exc}")

    raise RuntimeError("Text could not be extracted from this PDF. Use a text-based report PDF, not a scanned image PDF. " + " | ".join(errors))


def _normalise_text(text: str) -> str:
    text = (text or "").replace("\u00a0", " ")
    text = re.sub(r"[\t ]+", " ", text)
    return text


def _to_float(value: str) -> Optional[float]:
    try:
        return float(str(value).replace(",", "").strip())
    except Exception:
        return None


def _format_value(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:g}"


def _convert_unit(test: str, value: float, context: str) -> Tuple[float, str, bool]:
    ctx = (context or "").lower()
    converted = False
    unit = NORMAL_RANGES[test]["unit"]
    if test == "platelets" and ("lakh" in ctx or "lac" in ctx):
        return value * 100000, "lakhs/cumm", True
    if test == "wbc" and ("cumm" in ctx or "cells" in ctx or "/ul" in ctx or "/µl" in ctx):
        return value, "/µL", False
    if test == "rbc" and "million" in ctx:
        return value, "million/µL", False
    return value, unit, converted


def _line_should_be_skipped(line: str, test: str) -> bool:
    lower = line.lower()
    if test == "mch" and ("mchc" in lower or "haemoglobin con" in lower or "hemoglobin con" in lower or "corpuscular hemoglobin concentration" in lower):
        return True
    if test == "hemoglobin" and ("mean cell" in lower or "mch" in lower or "mchc" in lower or "corpuscular" in lower or "hba1c" in lower or "hb a1c" in lower):
        return True
    if test == "cholesterol" and ("ldl" in lower or "hdl" in lower):
        return True
    if test == "t3" and ("tsh" in lower or "t4" in lower):
        return True
    if test == "t4" and ("tsh" in lower or "t3" in lower):
        return True
    return False


def _extract_value_from_line(line: str, aliases: List[str], test: str) -> Tuple[Optional[float], str, Optional[float], bool]:
    if _line_should_be_skipped(line, test):
        return None, "", None, False

    alias_pattern = r"(?:" + "|".join(re.escape(a) for a in sorted(aliases, key=len, reverse=True)) + r")"
    number = r"([-+]?\d[\d,]*(?:\.\d+)?)"
    # Common table formats:
    # TEST VALUE UNIT REFERENCE
    # LYMPHOCYTE L 18 % 20 - 40
    # MCHC H 35.7 % 31.5 - 34.5
    patterns = [
        rf"\b{alias_pattern}\b\s*(?:[HL]\s*)?{number}\s*([^\n\r]*)",
        rf"\b{alias_pattern}\b[^\d\n\r-]{{0,55}}(?:[HL]\s*)?{number}\s*([^\n\r]*)",
        rf"{number}\s*([^\n\r]{{0,35}})\b{alias_pattern}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, line, flags=re.IGNORECASE)
        if not match:
            continue
        raw_value = _to_float(match.group(1))
        if raw_value is None:
            continue
        context = match.group(2) if len(match.groups()) >= 2 else ""
        value, unit, converted = _convert_unit(test, raw_value, context)
        return value, unit, raw_value, converted
    return None, "", None, False


def _find_value(text: str, test: str, aliases: List[str]) -> Tuple[Optional[float], str, Optional[float], bool]:
    text = _normalise_text(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # First pass: line-by-line to avoid values spilling from another row.
    for line in lines:
        lower = line.lower()
        if not any(re.search(rf"\b{re.escape(alias.lower())}\b", lower) for alias in aliases):
            continue
        value, unit, raw_value, converted = _extract_value_from_line(line, aliases, test)
        if value is not None:
            return value, unit, raw_value, converted

    # Fallback: full-text search for messy PDFs.
    value, unit, raw_value, converted = _extract_value_from_line(text, aliases, test)
    return value, unit, raw_value, converted


def analyze_values(report_text: str) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    for test, info in NORMAL_RANGES.items():
        value, detected_unit, raw_value, converted = _find_value(report_text, test, info["aliases"])
        if value is None:
            continue

        low, high = float(info["low"]), float(info["high"])
        if value < low:
            status = "Low"
            risk = info["low_risk"]
        elif value > high:
            status = "High"
            risk = info["high_risk"]
        else:
            status = "Normal"
            risk = "Value appears within the project reference range."

        display_value = _format_value(value)
        if test == "platelets" and converted and raw_value is not None:
            display_value = f"{raw_value:g} lakhs/cumm ({_format_value(value)} /µL)"

        found.append({
            "test": test.title() if test not in {"wbc", "rbc", "mcv", "mch", "mchc", "ldl", "hdl", "tsh", "t3", "t4", "sgpt", "sgot"} else test.upper(),
            "key": test,
            "value": display_value,
            "numeric_value": value,
            "normal_range": f"{low:g} - {high:g} {info['unit']}",
            "status": status,
            "meaning": MEDICAL_TERMS.get(test, "Medical test value found in the report."),
            "risk": risk,
        })
    return found


def _unique(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _category_flags(abnormal: List[Dict[str, Any]]) -> Dict[str, bool]:
    keys = {str(v.get("key", "")).lower() for v in abnormal}
    high = {str(v.get("key", "")).lower() for v in abnormal if str(v.get("status", "")).lower() == "high"}
    low = {str(v.get("key", "")).lower() for v in abnormal if str(v.get("status", "")).lower() == "low"}
    return {
        "lipid_high": bool(high & {"cholesterol", "ldl", "triglycerides"}),
        "hdl_low": "hdl" in low,
        "sugar_high": bool(high & {"glucose", "hba1c"}),
        "sugar_low": "glucose" in low,
        "thyroid": bool(keys & {"tsh", "t3", "t4"}),
        "cbc": bool(keys & {"hemoglobin", "wbc", "neutrophils", "lymphocytes", "eosinophils", "monocytes", "basophils", "rbc", "platelets", "hematocrit", "mcv", "mch", "mchc"}),
        "kidney": bool(keys & {"creatinine", "urea"}),
        "liver": bool(keys & {"sgpt", "sgot", "bilirubin"}),
        "vitamin": bool(keys & {"vitamin d", "vitamin b12"}),
    }


def build_rule_based_analysis(report_text: str) -> Dict[str, Any]:
    values = analyze_values(report_text)
    abnormal = [v for v in values if str(v.get("status", "")).lower() != "normal"]
    flags = _category_flags(abnormal)

    if abnormal:
        names = ", ".join(f"{v['test']} ({v['status']})" for v in abnormal)
        disease = "Some values need attention"
        summary = f"{len(values)} report values were detected. {len(abnormal)} value(s) need attention: {names}."
    elif values:
        disease = "No major abnormality detected in extracted values"
        summary = f"{len(values)} report values were detected and all appear within the project reference ranges."
    else:
        disease = "Values could not be clearly detected"
        summary = "The report text was read, but common numeric lab values were not clearly detected. Try a clearer text-based PDF."

    risk_factors = [f"{v['test']}: {v['risk']}" for v in abnormal]
    if not risk_factors:
        risk_factors = ["No major risk indicator was detected from the extracted common values."]

    diet = [
        "Prefer balanced meals with vegetables, fruits, whole grains, proteins, and enough water.",
        "Avoid self-medication and compare values with the reference range printed on the original report.",
    ]
    recommendations = [
        "Consult a certified doctor for final interpretation.",
        "Keep the original lab report and share it with your healthcare professional.",
        "Repeat or confirm testing only if advised by a doctor or if symptoms are present.",
    ]

    if flags["lipid_high"] or flags["hdl_low"]:
        diet += [
            "For lipid concerns, reduce fried food, trans fats, excess sugar, and processed snacks.",
            "Add fiber-rich foods such as oats, pulses, vegetables, fruits, and nuts in suitable portions.",
        ]
        recommendations += [
            "Discuss lipid profile results and cardiovascular risk with a doctor.",
            "Regular walking or exercise may help, if suitable for your health condition.",
        ]
    if flags["sugar_high"]:
        diet += [
            "For high sugar indicators, limit sweet drinks, refined sugar, and large portions of refined carbohydrates.",
            "Prefer controlled portions, high-fiber foods, and regular meal timing.",
        ]
        recommendations += ["Discuss glucose/HbA1c results with a doctor for diabetes risk assessment."]
    if flags["sugar_low"]:
        recommendations += ["Low sugar can become urgent if symptoms occur; seek medical advice promptly if dizziness, sweating, or faintness is present."]
    if flags["thyroid"]:
        recommendations += ["Discuss thyroid profile values with a doctor; thyroid interpretation depends on TSH, T3/T4, symptoms, and history."]
    if flags["cbc"]:
        diet += ["For CBC-related concerns, maintain adequate protein, iron, folate, B12, and hydration as appropriate for your case."]
        recommendations += ["CBC abnormalities should be interpreted with symptoms, infection history, and doctor review."]
    if flags["kidney"]:
        recommendations += ["Kidney-related markers should be reviewed with hydration status, urine tests, and medical history."]
    if flags["liver"]:
        diet += ["For liver enzyme concerns, avoid alcohol and unnecessary medicines unless prescribed."]
        recommendations += ["Liver enzyme changes should be reviewed with a doctor, especially if persistent or high."]
    if flags["vitamin"]:
        diet += ["For vitamin deficiency indicators, ask a doctor about diet, sunlight exposure, and supplement need."]

    return {
        "disease": disease,
        "summary": summary,
        "detected_values": values,
        "risk_factors": _unique(risk_factors),
        "recommendations": _unique(recommendations),
        "diet": " ".join(_unique(diet)),
        "solution": "Review abnormal values with a doctor, follow safe lifestyle guidance, and avoid making treatment decisions based only on this app.",
        "disclaimer": DISCLAIMER,
    }


def safe_json_loads(raw: str) -> Dict[str, Any]:
    if not raw:
        raise ValueError("Empty AI response")
    clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    match = re.search(r"\{.*\}", clean, flags=re.DOTALL)
    payload = match.group(0) if match else clean
    return json.loads(payload)


def merge_ai_with_rules(ai_data: Optional[Dict[str, Any]], rule_data: Dict[str, Any]) -> Dict[str, Any]:
    """Keep extracted numeric values from rule logic as source of truth and merge safe AI text only."""
    if not ai_data:
        return rule_data
    merged = dict(rule_data)
    for key in ["diet", "solution"]:
        if isinstance(ai_data.get(key), str) and ai_data[key].strip():
            merged[key] = ai_data[key].strip()
    if isinstance(ai_data.get("recommendations"), list):
        merged["recommendations"] = _unique(rule_data.get("recommendations", []) + [str(x) for x in ai_data["recommendations"] if str(x).strip()])
    merged["summary"] = rule_data.get("summary", merged.get("summary", ""))
    merged["disease"] = rule_data.get("disease", merged.get("disease", ""))
    merged["risk_factors"] = rule_data.get("risk_factors", merged.get("risk_factors", []))
    merged["detected_values"] = rule_data.get("detected_values", [])
    merged["disclaimer"] = DISCLAIMER
    return merged
