class PatientName {
    family string?  @description("Surname of the patient")
    given string[]?  @description("Given name(s) of the patient")
    prefix string?  @description("Mr., Mrs., Ms., Dr., etc.")
}

// Need a separate class for practitioner name because it confuse the model when
// the patient name and practitioner name are in the same report.
class PractitionerName {
    family string?  @description("Surname of the practitioner")
    given string[]?  @description("Given name(s) of the practitioner")
    prefix string?  @description("Mr., Mrs., Ms., Dr., etc.")
}

enum MaritalStatus {
    Married
    Single
    Divorced
    NeverMarried
}

class HomeAddress {
    line string
    city string
    state string
    postalCode string?
    country "US" | null
}

// Need a separate class for healthcare provider address because it confuse the model when
// the patient address and healthcare provider address are in the same report.
class HealthcareProviderAddress {
    line string
    city string
    state string
    postalCode string?
    country "US" | null
}

class Patient {
  name PatientName
  age int?
  gender "Male" | "Female" | null
  birthDate string?  @description("Date of birth of the patient in ISO-8601 format")
  address HomeAddress | null  @description("Residence address of the patient")
  phone string?
  email string?
  maritalStatus MaritalStatus | null
  primaryLanguage "English" | "Spanish" | null
}

class Practitioner {
  name PractitionerName
  address HealthcareProviderAddress | null
  phone string?
  email string?
}

class Immunization {
    vaccine_traits string[]?  @description("Text describing the name and traits of the immunization")
    status "completed" | null
    occurrenceDateTime string?  @description("ISO-8601 format for datetime including timezone")
}

class Substance {
    category "environment" | "food" | "medication" | "other" | null
    name string?
    manifestation string[]?  @description("Text describing the manifestation of the allergy or intolerance")
}

class Allergy {
    substance Substance[]  @description("The substance that the patient is allergic to")
}

// --- Functions ---

function ExtractPatient(record: string) -> Patient {
  client OpenRouterGoogleGemini2Flash
// client OpenRouterGPT4o
  prompt #"
    Extract the patient information using ONLY the information provided in the note.

    For address fields, be careful. Check whether the address is for the patient or for the healthcare provider.

    {{ _.role('user') }}

    {{ record }}

    {{ ctx.output_format }}
  "#
}

function ExtractPractitioner(record: string) -> Practitioner {
  client OpenRouterGoogleGemini2Flash
//   client OpenRouterGPT4o
  prompt #"
    Extract the healthcare provider's practitioner information using ONLY the information provided in the note.

    For address fields, be careful. Check whether the address is for the patient or for the healthcare provider.

    {{ _.role('user') }}

    {{ record }}

    {{ ctx.output_format }}
  "#
}

function ExtractImmunization(record: string) -> Immunization {
  client OpenRouterGoogleGemini2Flash
  prompt #"
    Extract details about any immunizations the patient has received.
    Use ONLY the information provided in the note.

    {{ _.role('user') }}

    {{ record }}

    {{ ctx.output_format }}
  "#
}

function ExtractAllergy(record: string) -> Allergy {
  client OpenRouterGoogleGemini2Flash
  prompt #"
    Extract details about any allergies or intolerances the patient has.
    Use ONLY the information provided in the note.

    {{ _.role('user') }}

    {{ record }}

    {{ ctx.output_format }}
    "#
}

// --- Tests ---

test ExtractPatient1 {
  functions [ExtractPatient]
  args {
    record #"
    This is about Mr. Fernando Amos Breitenberg. He's married. Now let's talk about his medical encounters.\n\nThe main one is a well child visit. This happened at the clinic. The visit started on December 23, 1992, at 01:08:42 and ended on the same day at 01:23:42, with timezone being +01:00. Mr. Breitenberg was looked after by Dr. Trent Krajcik. He was the one who did the whole procedure.\n\nMoving on, Mr. Breitenberg has an allergy. It's active and confirmed. He's allergic to shellfish. We've known this since April 2, 1994, at 12:08:42, with timezone as +02:00.\n\nFinally, all this happened at our healthcare provider in Quincy. It's located at 300 CONGRESS ST STE 203, Quincy, MA, 021690907, US.
    "#
  }
  @@assert({{ this.name.family == "Breitenberg" }})
  @@assert({{ "Fernando" in this.name.given }})
  @@assert({{ "Amos" in this.name.given }})
  @@assert({{ this.maritalStatus == "Married" }})
  @@assert({{ this.birthDate == none }})
}

test ExtractPatient2 {
  functions [ExtractPatient]
  args {
    record #"
    Ms. Marisol Rodríguez, who was born on December 1, 1995, and resides at her home at 547 Effertz Extension Unit 28, East Longmeadow, Massachusetts, 00000, is never married. She identifies Spanish as her primary language. She can be reached at her home phone number, which is 555-808-5474.\n\nIn the past, Marisol visited the ENCOMPASS HEALTH REHAB HOSPITAL OF WESTERN MASS on December 13, 2013, from 9:15:24 until 9:30:24 in Central European Standard Time for a postnatal visit. During this visit, Dr. Cletus Paucek, a primary performer, was the practitioner managing her care. You may reach out to Dr. Paucek at his work email, which is Cletus494.Paucek755@example.com.\n\nOf note, Marisol has a confirmed low criticality allergy towards shellfish, first noted on June 2, 1997, at 22:15:24 in Central Eastern Standard Time. Reactions to an exposure to shellfish in her case have varied. In some instances, she experiences a moderate eruption of skin. In severe cases, she has experienced anaphylaxis. More often, her symptoms are mild and include itching and coughing. Another noted allergy intolerance is currently active, yet the clinical details are not specified here.\n\nIn conclusion, based on the documented clinical data, Marisol has a history of postnatal follow-ups and confirmed food allergies that need to be managed, particularly regarding shellfish. She has also had encounters with a primary care practitioner, Dr. Paucek, who can be contacted for more in-depth knowledge about her medical history. The active allergy intolerance should also be further investigated for better management.\n\n
    "#
  }
  @@assert({{ this.name.family == "Rodríguez" }})
  @@assert({{ "Marisol" in this.name.given }})
  @@assert({{ this.birthDate == "1995-12-01" }})
  @@assert({{ this.address.line == "547 Effertz Extension Unit 28" }})
  @@assert({{ this.address.city == "East Longmeadow" }})
  @@assert({{ this.address.state == "Massachusetts" }})
  @@assert({{ this.address.postalCode == "00000" }})
  @@assert({{ this.address.country == "US" }})
  @@assert({{ this.phone == "555-808-5474" }})
  @@assert({{ this.primaryLanguage == "Spanish" }})
  @@assert({{ this.maritalStatus == "NeverMarried" }})
}

test ExtractPatient3 {
  functions [ExtractPatient]
  args {
    record #"
    Patient Information:\n- Full Name: Officially named Azucena Lore Durgan \n- Gender: Female\n- Date of Birth: October 20, 2008\n- Marital Status: Never Married\n\nContact Details:\n- Contact Number: Home phone is 555-374-5890\n- Address: Lives at 599 Ledner Park, Lowell, Massachusetts, 01850, US\n\nOther Information:\n- Primary Language: English (United States)\n\n
    "#
  }
  @@assert({{ this.name.family == "Durgan" }})
  @@assert({{ "Azucena" in this.name.given }})
  @@assert({{ "Lore" in this.name.given }})
  @@assert({{ this.gender == "Female" }})
  @@assert({{ this.birthDate == "2008-10-20" }})
  @@assert({{ this.maritalStatus == "NeverMarried" }})
  @@assert({{ this.primaryLanguage == "English" }})
}

test ExtractPractitioner1 {
  functions [ExtractPractitioner]
  args {
    record #"
    This is about Mr. Fernando Amos Breitenberg. He's married. Now let's talk about his medical encounters.\n\nThe main one is a well child visit. This happened at the clinic. The visit started on December 23, 1992, at 01:08:42 and ended on the same day at 01:23:42, with timezone being +01:00. Mr. Breitenberg was looked after by Dr. Trent Krajcik. He was the one who did the whole procedure.\n\nMoving on, Mr. Breitenberg has an allergy. It's active and confirmed. He's allergic to shellfish. We've known this since April 2, 1994, at 12:08:42, with timezone as +02:00.\n\nFinally, all this happened at our healthcare provider in Quincy. It's located at 300 CONGRESS ST STE 203, Quincy, MA, 021690907, US.
    "#
  }
  @@assert({{ this.name.family == "Krajcik" }})
  @@assert({{ "Trent" in this.name.given }})
  @@assert({{ this.name.prefix == "Dr." }})
  @@assert({{ this.address.line == "300 CONGRESS ST STE 203" }})
  @@assert({{ this.address.city == "Quincy" }})
  @@assert({{ this.address.state == "MA" }})
  @@assert({{ this.address.postalCode == "021690907" }})
  @@assert({{ this.address.country == "US" }})
}

test ExtractPractitioner2 {
  functions [ExtractPractitioner]
  args {
    record #"
    Ms. Marisol Rodríguez, who was born on December 1, 1995, and resides at her home at 547 Effertz Extension Unit 28, East Longmeadow, Massachusetts, 00000, is never married. She identifies Spanish as her primary language. She can be reached at her home phone number, which is 555-808-5474.\n\nIn the past, Marisol visited the ENCOMPASS HEALTH REHAB HOSPITAL OF WESTERN MASS on December 13, 2013, from 9:15:24 until 9:30:24 in Central European Standard Time for a postnatal visit. During this visit, Dr. Cletus Paucek, a primary performer, was the practitioner managing her care. You may reach out to Dr. Paucek at his work email, which is Cletus494.Paucek755@example.com.\n\nOf note, Marisol has a confirmed low criticality allergy towards shellfish, first noted on June 2, 1997, at 22:15:24 in Central Eastern Standard Time. Reactions to an exposure to shellfish in her case have varied. In some instances, she experiences a moderate eruption of skin. In severe cases, she has experienced anaphylaxis. More often, her symptoms are mild and include itching and coughing. Another noted allergy intolerance is currently active, yet the clinical details are not specified here.\n\nIn conclusion, based on the documented clinical data, Marisol has a history of postnatal follow-ups and confirmed food allergies that need to be managed, particularly regarding shellfish. She has also had encounters with a primary care practitioner, Dr. Paucek, who can be contacted for more in-depth knowledge about her medical history. The active allergy intolerance should also be further investigated for better management.\n\n
    "#
  }
  @@assert({{ this.name.family == "Paucek" }})
  @@assert({{ "Cletus" in this.name.given }})
  @@assert({{ this.name.prefix == "Dr." }})
  @@assert({{ this.email == "Cletus494.Paucek755@example.com" }})
}

test ExtractImmunization1 {
  functions [ExtractImmunization]
  args {
    record #"
    A clinical note for Ms. Sonia María Bañuelos: \n\nOn December 24, 2013, at 16:59:45 GMT+1, Ms. Bañuelos received an injectable, preservative-free, seasonal influenza vaccine. This immunization procedure was completed smoothly. \n\nRegarding her personal information, Ms. Bañuelos, identifies as female and is not a multiple birth individual, meaning she doesn't have any twins or triplets. Her official residence is listed as 130 Rempel Vale, Boston, Massachusetts, 02111, United States. Moreover, it's noted that her primary language is Spanish. Hence, all communication with her should ideally be in Spanish for ensuring comprehension.\n\n\n
    "#
  }
  @@assert({{ this.occurrenceDateTime == "2013-12-24T16:59:45+01:00" }})
  @@assert({{ this.status == "completed" }})
}

test ExtractAllergy1 {
  functions [ExtractAllergy]
  args {
    record #"
    Clinical Note:\n\n- Patient: Mr. Vince Maria Bergnaum\n- Gender: Male\n- Date of Birth: September 30, 1978\n- Allergy Status: Active\n- Alarm Verification: Confirmed\n- Type of Allergy: Environmental\n- Recorded Date of Allergy: July 11, 1999 at 09:03:29 GMT+02:00\n- Relation between resources: The indicated information describes an environmental allergy for Mr. Vince Maria Bergnaum, which has been confirmed and is active as recorded on July 11, 1999 at 09:03:29 GMT+02:00.\n\n
    "#
  }
  @@assert({{ this.substance[0].category == "environment" }})
}

test ExtractAllergy2 {
  functions [ExtractAllergy]
  args {
    record #"
    This is about Mr. Fernando Amos Breitenberg. He's married. Now let's talk about his medical encounters.\n\nThe main one is a well child visit. This happened at the clinic. The visit started on December 23, 1992, at 01:08:42 and ended on the same day at 01:23:42, with timezone being +01:00. Mr. Breitenberg was looked after by Dr. Trent Krajcik. He was the one who did the whole procedure.\n\nMoving on, Mr. Breitenberg has an allergy. It's active and confirmed. He's allergic to shellfish. We've known this since April 2, 1994, at 12:08:42, with timezone as +02:00.\n\nFinally, all this happened at our healthcare provider in Quincy. It's located at 300 CONGRESS ST STE 203, Quincy, MA, 021690907, US.
    "#
  }
  @@assert({{ "shellfish" in this.substance[0].name }})
  @@assert({{ this.substance[0].category == "food" }})
}

test ExtractAllergy3 {
  functions [ExtractAllergy]
  args {
    record #"
    Ms. Marisol Rodríguez, who was born on December 1, 1995, and resides at her home at 547 Effertz Extension Unit 28, East Longmeadow, Massachusetts, 00000, is never married. She identifies Spanish as her primary language. She can be reached at her home phone number, which is 555-808-5474.\n\nIn the past, Marisol visited the ENCOMPASS HEALTH REHAB HOSPITAL OF WESTERN MASS on December 13, 2013, from 9:15:24 until 9:30:24 in Central European Standard Time for a postnatal visit. During this visit, Dr. Cletus Paucek, a primary performer, was the practitioner managing her care. You may reach out to Dr. Paucek at his work email, which is Cletus494.Paucek755@example.com.\n\nOf note, Marisol has a confirmed low criticality allergy towards shellfish, first noted on June 2, 1997, at 22:15:24 in Central Eastern Standard Time. Reactions to an exposure to shellfish in her case have varied. In some instances, she experiences a moderate eruption of skin. In severe cases, she has experienced anaphylaxis. More often, her symptoms are mild and include itching and coughing. Another noted allergy intolerance is currently active, yet the clinical details are not specified here.\n\nIn conclusion, based on the documented clinical data, Marisol has a history of postnatal follow-ups and confirmed food allergies that need to be managed, particularly regarding shellfish. She has also had encounters with a primary care practitioner, Dr. Paucek, who can be contacted for more in-depth knowledge about her medical history. The active allergy intolerance should also be further investigated for better management.\n\n
    "#
  }
  @@assert({{ "shellfish" in this.substance[0].name }})
  @@assert({{ this.substance[0].category == "food" }})
}