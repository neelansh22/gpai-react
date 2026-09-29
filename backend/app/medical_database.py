"""
Simple medical database for common conditions
This provides reliable medical descriptions and preventive measures
(Ported from the original Streamlit gpAssistant app)
"""

MEDICAL_DATABASE = {
    "common cold": {
        "description": "The common cold is a viral infection of your nose and throat (upper respiratory tract). It's usually harmless, although it might not feel that way.",
        "common_causes": ["Rhinoviruses (most common)", "Coronaviruses", "Respiratory syncytial virus (RSV)", "Close contact with infected persons", "Touching contaminated surfaces"],
        "symptoms": ["Runny or stuffy nose", "Sore throat", "Cough", "Congestion", "Slight body aches or mild headache", "Sneezing", "Low-grade fever", "Generally feeling unwell"],
        "preventive_measures": ["Wash hands frequently with soap and water", "Avoid touching face, especially nose and mouth", "Stay away from people who are sick", "Get adequate sleep and maintain good nutrition", "Stay hydrated with plenty of fluids"],
        "immediate_relief": ["Rest and get plenty of sleep", "Drink warm liquids like tea or warm water with honey", "Use a humidifier or breathe steam from hot shower", "Gargle with salt water for sore throat", "Use saline nasal drops for congestion"]
    },
    "headache": {
        "description": "A headache is pain or discomfort in the head, scalp, or neck. Most headaches are not serious, but some may indicate a more serious condition.",
        "common_causes": ["Tension and stress", "Dehydration", "Eye strain", "Poor posture", "Lack of sleep", "Certain foods or alcohol", "Hormonal changes"],
        "symptoms": ["Dull, aching head pain", "Sensation of tightness across forehead", "Tenderness around scalp, neck, and shoulders", "Pressure behind the eyes", "Sensitivity to light or sound"],
        "preventive_measures": ["Maintain regular sleep schedule", "Stay well hydrated throughout the day", "Manage stress through relaxation techniques", "Maintain good posture, especially when working", "Take regular breaks from screens"],
        "immediate_relief": ["Rest in a quiet, dark room", "Apply cold or warm compress to head or neck", "Gently massage temples and neck", "Stay hydrated with water", "Practice deep breathing exercises"]
    },
    "fever": {
        "description": "Fever is a temporary increase in body temperature, often due to an infection. It's a sign that your body is fighting off an infection.",
        "common_causes": ["Viral infections (most common)", "Bacterial infections", "Heat exhaustion", "Certain medications", "Inflammatory conditions"],
        "symptoms": ["Body temperature above 100.4°F (38°C)", "Chills and shivering", "Headache", "Muscle aches", "Loss of appetite", "Dehydration", "General weakness"],
        "preventive_measures": ["Practice good hygiene and handwashing", "Avoid close contact with sick individuals", "Stay up to date with vaccinations", "Maintain a healthy immune system", "Get adequate rest and nutrition"],
        "immediate_relief": ["Rest and get plenty of sleep", "Drink plenty of fluids to prevent dehydration", "Wear lightweight clothing", "Use cool, damp washcloth on forehead", "Take lukewarm baths (not cold)"]
    },
    "cough": {
        "description": "A cough is a reflex action that helps clear your airways of mucus and irritants. It can be acute (lasting less than 3 weeks) or chronic.",
        "common_causes": ["Viral respiratory infections", "Allergies", "Asthma", "Acid reflux", "Smoking or exposure to irritants", "Postnasal drip"],
        "symptoms": ["Dry or productive cough", "Throat irritation", "Chest discomfort", "Wheezing or shortness of breath", "Mucus production"],
        "preventive_measures": ["Avoid smoking and secondhand smoke", "Stay away from known allergens", "Wash hands frequently", "Stay hydrated", "Use air purifiers to reduce irritants"],
        "immediate_relief": ["Stay hydrated with warm liquids", "Use honey to soothe throat (not for children under 1 year)", "Breathe humid air from shower or humidifier", "Elevate head while sleeping", "Avoid irritants like strong perfumes or smoke"]
    },
    "nausea": {
        "description": "Nausea is the feeling of unease and discomfort in the upper stomach with an involuntary urge to vomit.",
        "common_causes": ["Viral gastroenteritis", "Food poisoning", "Motion sickness", "Pregnancy", "Medication side effects", "Stress and anxiety"],
        "symptoms": ["Feeling of queasiness", "Urge to vomit", "Stomach discomfort", "Loss of appetite", "Sweating", "Dizziness"],
        "preventive_measures": ["Practice good food hygiene", "Eat small, frequent meals", "Avoid strong odors", "Manage stress levels", "Stay hydrated"],
        "immediate_relief": ["Sip clear fluids slowly (water, clear broths)", "Eat bland foods like crackers or toast", "Get fresh air and avoid strong smells", "Rest in a comfortable position", "Try ginger tea or ginger supplements"]
    },
    "diarrhea": {
        "description": "Diarrhea is a condition characterized by frequent, loose, or watery bowel movements. It can be acute or chronic.",
        "common_causes": ["Viral infections (e.g., norovirus)", "Bacterial infections (e.g., E. coli)", "Food intolerances (e.g., lactose intolerance)", "Medications (e.g., antibiotics)", "Stress and anxiety"],
        "symptoms": ["Frequent loose or watery stools", "Abdominal cramps", "Bloating", "Nausea", "Urgent need to have a bowel movement"],
        "preventive_measures": ["Wash hands frequently", "Avoid contaminated food and water", "Cook food thoroughly", "Stay hydrated", "Manage stress"],
        "immediate_relief": ["Stay hydrated with oral rehydration solutions", "Eat bland foods (BRAT diet: bananas, rice, applesauce, toast)", "Avoid dairy products and fatty foods", "Rest and avoid strenuous activities"]
    },
    "psoriasis": {
        "description": "Psoriasis is a chronic autoimmune skin condition that causes rapid skin cell growth, resulting in scaling and inflammation.",
        "common_causes": ["Genetic predisposition", "Immune system dysfunction", "Stress", "Infections", "Certain medications", "Skin injuries"],
        "symptoms": ["Red patches of skin covered with silvery scales", "Dry, cracked skin that may bleed", "Itching, burning, or soreness", "Thickened or ridged nails", "Stiff and swollen joints"],
        "preventive_measures": ["Manage stress", "Avoid skin trauma", "Moisturize regularly", "Limit alcohol and smoking", "Avoid known triggers"],
        "immediate_relief": ["Apply medicated moisturizers", "Take oatmeal or Epsom salt baths", "Use topical corticosteroids", "Avoid scratching", "Use light therapy if prescribed"]
    },
    "varicose veins": {
        "description": "Varicose veins are enlarged, twisted veins caused by valve malfunction, leading to poor circulation usually in the legs.",
        "common_causes": ["Genetics", "Pregnancy", "Obesity", "Prolonged standing", "Age-related wear and tear"],
        "symptoms": ["Bulging, bluish veins", "Aching or heaviness in legs", "Swelling", "Throbbing or cramping", "Skin discoloration"],
        "preventive_measures": ["Regular exercise", "Maintain healthy weight", "Elevate legs", "Avoid long standing/sitting", "Wear compression stockings"],
        "immediate_relief": ["Elevate legs", "Apply cold compress", "Massage gently", "Use compression socks", "Avoid restrictive clothing"]
    },
    "typhoid": {
        "description": "Typhoid is a bacterial infection caused by Salmonella typhi, spread through contaminated food and water.",
        "common_causes": ["Contaminated food and water", "Poor sanitation", "Close contact with infected individuals"],
        "symptoms": ["High fever", "Weakness", "Abdominal pain", "Constipation or diarrhea", "Rash"],
        "preventive_measures": ["Drink clean water", "Wash hands frequently", "Cook food thoroughly", "Vaccination in endemic areas"],
        "immediate_relief": ["Start antibiotics promptly", "Stay hydrated", "Eat soft, digestible food", "Rest well", "Use paracetamol for fever"]
    },
    "chicken pox": {
        "description": "Chickenpox is a viral infection that causes an itchy rash and red spots or blisters all over the body.",
        "common_causes": ["Varicella-zoster virus", "Airborne transmission", "Direct contact with blisters"],
        "symptoms": ["Itchy rash", "Blisters and scabs", "Fever", "Fatigue", "Loss of appetite"],
        "preventive_measures": ["Varicella vaccination", "Avoid contact with infected persons", "Good hygiene practices"],
        "immediate_relief": ["Calamine lotion", "Oatmeal baths", "Antihistamines", "Paracetamol for fever", "Plenty of fluids"]
    },
    "impetigo": {
        "description": "Impetigo is a contagious bacterial skin infection, common among children, causing red sores that can rupture and ooze.",
        "common_causes": ["Staphylococcus aureus", "Streptococcus pyogenes", "Poor hygiene", "Warm, humid conditions"],
        "symptoms": ["Red sores or blisters", "Honey-colored crusts", "Itching", "Swollen lymph nodes"],
        "preventive_measures": ["Good hygiene", "Avoid sharing personal items", "Keep wounds clean", "Treat eczema or other skin conditions"],
        "immediate_relief": ["Topical antibiotics", "Oral antibiotics for severe cases", "Keep area clean and dry", "Avoid scratching"]
    },
    "dengue": {
        "description": "Dengue is a mosquito-borne viral infection causing flu-like symptoms and potentially fatal complications.",
        "common_causes": ["Bite from Aedes aegypti mosquito", "Exposure to stagnant water", "Endemic travel"],
        "symptoms": ["High fever", "Severe headache", "Pain behind eyes", "Muscle and joint pain", "Rash", "Bleeding"],
        "preventive_measures": ["Avoid mosquito bites", "Use mosquito nets and repellents", "Eliminate stagnant water", "Wear protective clothing"],
        "immediate_relief": ["Hydration with ORS or fluids", "Paracetamol for fever", "Avoid NSAIDs (can cause bleeding)", "Rest"]
    },
    "fungal infection": {
        "description": "Fungal infections are caused by fungi affecting skin, nails, or internal organs.",
        "common_causes": ["Warm, moist environments", "Poor hygiene", "Weakened immune system", "Close contact with infected people or animals"],
        "symptoms": ["Itchy or scaly skin", "Red rash", "Peeling or cracking skin", "Discolored nails"],
        "preventive_measures": ["Keep skin dry and clean", "Avoid sharing towels or clothes", "Wear breathable clothing", "Use antifungal powders"],
        "immediate_relief": ["Apply antifungal creams or powders", "Keep affected area dry", "Avoid tight clothing", "Seek medical advice for persistent infections"]
    },
    "pneumonia": {
        "description": "Pneumonia is an infection that inflames air sacs in one or both lungs, which may fill with fluid or pus.",
        "common_causes": ["Bacteria (e.g. Streptococcus pneumoniae)", "Viruses (e.g. influenza)", "Fungi", "Inhalation of harmful substances"],
        "symptoms": ["Chest pain when breathing", "Cough with phlegm", "Fever and chills", "Shortness of breath", "Fatigue"],
        "preventive_measures": ["Vaccination (pneumococcal, flu)", "Good hygiene", "Avoid smoking", "Manage chronic diseases"],
        "immediate_relief": ["Antibiotics or antivirals", "Rest", "Hydration", "Use of humidifier", "Monitor oxygen levels"]
    },
    "dimorphic haemorrhoids": {
        "description": "Dimorphic hemorrhoids refer to a condition involving both internal and external piles, leading to discomfort and bleeding.",
        "common_causes": ["Chronic constipation", "Straining during bowel movements", "Low-fiber diet", "Sedentary lifestyle"],
        "symptoms": ["Rectal bleeding", "Painful defecation", "Itching", "Lumps around the anus"],
        "preventive_measures": ["High-fiber diet", "Stay hydrated", "Avoid straining", "Exercise regularly"],
        "immediate_relief": ["Warm sitz baths", "Topical creams", "Oral pain relievers", "Cold compress", "Avoid sitting for long periods"]
    },
    "arthritis": {
        "description": "Arthritis is inflammation of one or more joints, causing pain and stiffness that can worsen with age.",
        "common_causes": ["Wear and tear (osteoarthritis)", "Autoimmune disease (rheumatoid arthritis)", "Infections", "Genetics"],
        "symptoms": ["Joint pain", "Swelling", "Stiffness", "Reduced range of motion"],
        "preventive_measures": ["Maintain healthy weight", "Regular, low-impact exercise", "Avoid joint injuries", "Healthy diet"],
        "immediate_relief": ["Use of NSAIDs", "Hot and cold therapy", "Gentle stretching", "Assistive devices to reduce strain"]
    },
    "acne": {
        "description": "Acne is a common skin condition that occurs when hair follicles become clogged with oil and dead skin cells.",
        "common_causes": ["Excess oil production", "Hormonal changes", "Bacteria", "Certain medications", "Genetics"],
        "symptoms": ["Whiteheads and blackheads", "Pimples or pustules", "Cystic lesions", "Scarring"],
        "preventive_measures": ["Cleanse skin gently", "Avoid oily cosmetics", "Eat a balanced diet", "Manage stress"],
        "immediate_relief": ["Topical treatments (benzoyl peroxide, salicylic acid)", "Avoid picking or squeezing", "Use non-comedogenic products", "Consult dermatologist for severe cases"]
    },
    "bronchial asthma": {
        "description": "Bronchial asthma is a chronic respiratory condition where airways become inflamed, narrow, and swell, producing extra mucus.",
        "common_causes": ["Allergens (pollen, dust)", "Air pollution", "Cold air", "Exercise", "Respiratory infections"],
        "symptoms": ["Shortness of breath", "Wheezing", "Chest tightness", "Coughing, especially at night"],
        "preventive_measures": ["Identify and avoid triggers", "Use inhaled corticosteroids", "Vaccinate against flu and pneumonia", "Monitor lung function"],
        "immediate_relief": ["Use a rescue inhaler (bronchodilator)", "Sit upright and breathe slowly", "Seek medical help for severe attacks"]
    },
    "hypertension": {
        "description": "Hypertension is high blood pressure, a condition where the force of blood against artery walls is consistently too high.",
        "common_causes": ["Genetics", "Unhealthy diet", "Lack of physical activity", "Chronic stress", "Obesity"],
        "symptoms": ["Often asymptomatic", "Headaches", "Shortness of breath", "Nosebleeds (in severe cases)"],
        "preventive_measures": ["Limit salt intake", "Exercise regularly", "Avoid tobacco and alcohol", "Manage stress", "Monitor blood pressure"],
        "immediate_relief": ["Sit and relax", "Take prescribed antihypertensive medication", "Avoid stimulants like caffeine", "Deep breathing exercises"]
    },
    "migraine": {
        "description": "Migraine is a neurological condition characterized by intense, pulsing headaches, often accompanied by nausea and sensitivity to light or sound.",
        "common_causes": ["Hormonal changes", "Stress", "Certain foods and drinks", "Sleep disturbances", "Environmental factors"],
        "symptoms": ["Throbbing head pain", "Nausea or vomiting", "Sensitivity to light/sound", "Visual disturbances (auras)"],
        "preventive_measures": ["Identify and avoid triggers", "Maintain consistent sleep schedule", "Stay hydrated", "Use preventive medication if prescribed"],
        "immediate_relief": ["Rest in a dark, quiet room", "Cold compress on forehead", "Take migraine-specific painkillers", "Hydration and light food intake"]
    },
    "cervical spondylosis": {
        "description": "Cervical spondylosis is age-related wear and tear affecting spinal disks in the neck, leading to neck pain and stiffness.",
        "common_causes": ["Degeneration with age", "Neck injuries", "Poor posture", "Repetitive strain"],
        "symptoms": ["Neck pain and stiffness", "Headaches", "Shoulder pain", "Tingling or numbness in limbs"],
        "preventive_measures": ["Correct posture", "Regular neck exercises", "Avoid strain and heavy lifting", "Use ergonomic furniture"],
        "immediate_relief": ["Apply heat or cold packs", "Neck support or brace", "Pain relief medications", "Gentle stretching"]
    },
    "jaundice": {
        "description": "Jaundice is a condition characterized by yellowing of the skin and eyes due to elevated bilirubin levels in the blood.",
        "common_causes": ["Liver diseases (hepatitis, cirrhosis)", "Gallstones", "Hemolytic anemia", "Infections"],
        "symptoms": ["Yellowing of skin and eyes", "Dark urine", "Pale stools", "Fatigue", "Abdominal pain"],
        "preventive_measures": ["Avoid alcohol abuse", "Vaccination for hepatitis", "Safe food and water practices", "Avoid unnecessary medications"],
        "immediate_relief": ["Identify and treat underlying cause", "Hydration and rest", "Low-fat diet", "Avoid hepatotoxic substances"]
    },
    "malaria": {
        "description": "Malaria is a mosquito-borne disease caused by Plasmodium parasites that infect red blood cells.",
        "common_causes": ["Bite of infected Anopheles mosquito", "Travel to endemic areas"],
        "symptoms": ["Cyclic fevers", "Chills and sweating", "Nausea and vomiting", "Headache", "Fatigue"],
        "preventive_measures": ["Use insect repellents and bed nets", "Take antimalarial prophylaxis", "Avoid stagnant water", "Wear full-sleeve clothes"],
        "immediate_relief": ["Antimalarial medications", "Hydration", "Rest", "Monitor for complications"]
    },
    "uti": {
        "description": "Urinary tract infection (UTI) is an infection in any part of the urinary system, commonly caused by bacteria.",
        "common_causes": ["E. coli infection", "Poor hygiene", "Urinary retention", "Catheter use"],
        "symptoms": ["Burning sensation during urination", "Frequent urge to urinate", "Cloudy or strong-smelling urine", "Pelvic pain"],
        "preventive_measures": ["Stay hydrated", "Urinate after intercourse", "Wipe front to back", "Avoid harsh soaps in genital area"],
        "immediate_relief": ["Increase fluid intake", "Use antibiotics as prescribed", "Pain relievers", "Cranberry juice (supportive)"]
    },
    "allergy": {
        "description": "Allergy is an immune system reaction to a foreign substance that's not typically harmful to the body.",
        "common_causes": ["Pollen", "Dust mites", "Animal dander", "Certain foods or medications"],
        "symptoms": ["Sneezing", "Runny nose", "Itchy eyes or skin", "Hives", "Anaphylaxis (severe cases)"],
        "preventive_measures": ["Identify and avoid triggers", "Use air filters", "Keep environment clean", "Allergy testing and immunotherapy"],
        "immediate_relief": ["Antihistamines", "Nasal decongestants", "Cool compresses for skin", "Epinephrine injection for anaphylaxis"]
    },
    "gastroesophageal reflux disease": {
        "description": "GERD is a chronic condition where stomach acid frequently flows back into the esophagus, irritating its lining.",
        "common_causes": ["Weak lower esophageal sphincter", "Obesity", "Pregnancy", "Hiatal hernia", "Certain foods"],
        "symptoms": ["Heartburn", "Chest pain", "Regurgitation", "Sore throat", "Difficulty swallowing"],
        "preventive_measures": ["Avoid trigger foods", "Eat smaller meals", "Maintain healthy weight", "Elevate head while sleeping"],
        "immediate_relief": ["Antacids", "H2 blockers or PPIs", "Avoid lying down after eating", "Chewing gum (increases saliva)"]
    },
    "drug reaction": {
        "description": "A drug reaction is an unintended and harmful reaction to a medication.",
        "common_causes": ["Allergic response to medication", "Incorrect dosage", "Drug interactions", "Genetic predisposition"],
        "symptoms": ["Rash", "Swelling", "Nausea", "Breathing difficulty", "Anaphylaxis"],
        "preventive_measures": ["Inform doctor of allergies", "Avoid self-medication", "Read drug labels carefully", "Genetic testing (for specific drugs)"],
        "immediate_relief": ["Discontinue the drug", "Administer antihistamines or epinephrine", "Seek emergency care for severe reactions", "Monitor vital signs"]
    },
    "peptic ulcer disease": {
        "description": "Peptic ulcer disease involves sores in the stomach lining or upper intestine, often caused by H. pylori or NSAID use.",
        "common_causes": ["Helicobacter pylori infection", "NSAIDs (aspirin, ibuprofen)", "Stress", "Smoking"],
        "symptoms": ["Burning stomach pain", "Bloating", "Nausea", "Dark stools"],
        "preventive_measures": ["Limit NSAID use", "Avoid smoking and alcohol", "Eat balanced meals", "Treat H. pylori infections"],
        "immediate_relief": ["Antacids", "Proton pump inhibitors", "Avoid spicy/acidic foods", "Small, frequent meals"]
    },
    "diabetes": {
        "description": "Diabetes is a chronic condition that affects how the body processes blood sugar (glucose).",
        "common_causes": ["Genetic predisposition", "Obesity", "Lack of physical activity", "Insulin resistance"],
        "symptoms": ["Frequent urination", "Increased thirst", "Fatigue", "Blurred vision", "Slow-healing wounds"],
        "preventive_measures": ["Maintain healthy weight", "Exercise regularly", "Balanced diet low in sugar", "Regular blood sugar monitoring"],
        "immediate_relief": ["Take insulin or medication as prescribed", "Eat fiber-rich, low-sugar food", "Hydration", "Monitor blood glucose levels"]
    },
    "fatigue": {
        "description": "Fatigue is extreme tiredness and lack of energy that doesn't improve with rest. It can affect daily activities and quality of life.",
        "common_causes": ["Insufficient sleep", "Stress and mental health issues", "Poor nutrition", "Lack of physical activity", "Viral infections", "Chronic medical conditions"],
        "symptoms": ["Persistent tiredness", "Lack of energy", "Difficulty concentrating", "Muscle weakness", "Mood changes", "Reduced motivation"],
        "preventive_measures": ["Maintain regular sleep schedule", "Eat balanced, nutritious meals", "Exercise regularly but moderately", "Manage stress effectively", "Stay hydrated"],
        "immediate_relief": ["Prioritize rest and adequate sleep", "Take short power naps (15-20 minutes)", "Stay hydrated with water", "Eat energy-rich, healthy snacks", "Take gentle walks in fresh air"]
    }
}


def get_medical_info(condition: str) -> dict:
    """Return structured medical information for a given condition (dict, not markdown)."""
    condition_lower = condition.lower().strip()

    if condition_lower in MEDICAL_DATABASE:
        info = MEDICAL_DATABASE[condition_lower]
        matched = condition_lower
    else:
        matches = [key for key in MEDICAL_DATABASE if condition_lower in key or key in condition_lower]
        if matches:
            matched = matches[0]
            info = MEDICAL_DATABASE[matched]
        else:
            return {
                "condition": condition.title(),
                "matched": False,
                "description": "No specific entry found in our local database for this condition.",
                "common_causes": [],
                "symptoms": [],
                "preventive_measures": [
                    "Rest and get adequate sleep",
                    "Stay well hydrated with water",
                    "Eat nutritious, easily digestible foods",
                    "Monitor your symptoms closely",
                ],
                "immediate_relief": [
                    "Avoid strenuous activities",
                    "Seek medical attention if symptoms persist or worsen",
                ],
            }

    return {
        "condition": matched.title(),
        "matched": True,
        "description": info["description"],
        "common_causes": info["common_causes"],
        "symptoms": info["symptoms"],
        "preventive_measures": info["preventive_measures"],
        "immediate_relief": info["immediate_relief"],
    }
