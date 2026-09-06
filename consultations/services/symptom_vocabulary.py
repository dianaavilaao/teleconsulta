"""
Vocabulario canónico de síntomas (español), basado en los encabezados de
MedlinePlus. Se usa como referencia dentro del prompt de
`symptom_extraction.py` para guiar al modelo hacia términos estandarizados
— no se fuerza coincidencia exacta contra esta lista.
"""

SYMPTOM_VOCABULARY = {
    "Dolor abdominal": ["Abdomen, dolor", "Dolor de barriga"],
    "Acidez estomacal": [],
    "Atragantamiento": [],
    "Dolor de cabeza": ["Cabeza, dolor de"],
    "Enfermedades causadas por el calor": ["Calor, enfermedades causadas por el", "Insolación"],
    "Ciática": [],
    "Picazón": ["Comezón", "Escocer", "Picor", "Prurito"],
    "Problemas del habla y de la comunicación": ["Comunicación, problemas de", "Habla y comunicación, problemas de"],
    "Congelación": ["Congelamiento"],
    "Estreñimiento": ["Constipación"],
    "Moretones": ["Contusiones", "Equimosis", "Golpes", "Hematomas", "Magulladuras"],
    "Hipotermia": ["Daño causado por clima frío", "Frío, daño causado por"],
    "Deshidratación": ["Sed"],
    "Desmayo": ["Desvanecimiento", "Síncope"],
    "Diarrea": ["Disentería"],
    "Problemas respiratorios": ["Dificultad respiratoria", "Disnea", "Taquipnea"],
    "Hemorragia gastrointestinal": ["Sangrado gastrointestinal", "Digestivo, sangrado del aparato"],
    "Dolor": [],
    "Dolor crónico": [],
    "Dolor de pecho": [],
    "Dolor pélvico": ["Pelvis, dolor"],
    "Edema": ["Hidropesía", "Hinchazón"],
    "Mareo (cinetosis)": ["Enfermedad por movimiento"],
    "Mareo y vértigo": ["Equilibrio, trastornos del", "Vértigo"],
    "Fatiga": [],
    "Fenómeno de Raynaud": [],
    "Fiebre": [],
    "Gas": [],
    "Mal aliento": ["Halitosis"],
    "Hemorragia": ["Sangrado"],
    "Ictericia": [],
    "Indigestión": [],
    "Náusea y vómitos": ["Vómito", "Náuseas"],
    "Sangrado vaginal": [],
    "Tartamudez": [],
    "Tos": [],
    "Urticaria": [],
}
