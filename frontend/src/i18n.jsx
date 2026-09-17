import { createContext, useContext, useMemo, useState } from "react";

const messages = {
  en: { home: "Home", criminalList: "Criminal List", uploadDoc: "Upload Doc", logOut: "Log out", language: "Language", search: "Search", close: "Close", clearSelection: "Clear selection", aiInsight: "AI insight", lastSeen: "Last seen", recordsOnFile: "Records on file", tracedConnections: "Traced connections", linksKnown: "Links between known associates", crimeFrequency: "Crime tag frequency", citiesWatch: "Cities under watch", pinned: "Currently Pinned", noWorking: "Not working on anyone currently", caseHistory: "Case history", crimesCommitted: "Crimes committed", status: "Status", familyKnown: "Family known", dateBirth: "Date of birth", height: "Height", investigatorWorkspace: "Investigator workspace", networkAnalysis: "Network analysis", connections: "Connections", aiInvestigator: "AI investigator", investigatorAnalysis: "Investigator analysis", askAI: "Ask AI", age: "Age", closeFile: "Close file", addToList: "Add to list", removeFromList: "Remove from list", loading: "Loading…", loadingRecords: "Loading records…", noRecords: "No records found in the database.", noSearchMatches: "No case file matches that search.", searchResults: "files matched", criminalsOnFile: "criminals on file", basedIn: "based in", uploadAnalyze: "Upload and analyze records", recordSource: "Record source", upload: "Upload", noDocuments: "No documents uploaded yet.", openOriginal: "Open original document", review: "Review", closeDocument: "Close", reset: "Reset", retry: "Retry", fit: "Fit", selectedPerson: "Selected person", zoomIn: "Zoom in", zoomOut: "Zoom out", map: "Map", network: "Network", openFile: "Open file", unpin: "Unpin", onTheList: "On the list", noCases: "No cases added yet", tracked: "Criminals currently tracked" },
  hi: { home: "होम", criminalList: "अपराधी सूची", uploadDoc: "दस्तावेज़ अपलोड करें", logOut: "लॉग आउट", language: "भाषा", search: "खोजें", close: "बंद करें", clearSelection: "चयन हटाएं", aiInsight: "एआई जानकारी", lastSeen: "अंतिम बार देखा गया", recordsOnFile: "रिकॉर्ड", tracedConnections: "ट्रेस किए गए संबंध", linksKnown: "ज्ञात सहयोगियों के बीच संबंध", crimeFrequency: "अपराध टैग आवृत्ति", citiesWatch: "निगरानी वाले शहर", pinned: "वर्तमान में पिन किए गए", noWorking: "अभी किसी पर काम नहीं हो रहा", caseHistory: "मामले का इतिहास", crimesCommitted: "किए गए अपराध", status: "स्थिति", familyKnown: "ज्ञात परिवार", dateBirth: "जन्म तिथि", height: "कद", investigatorWorkspace: "जांचकर्ता कार्यक्षेत्र", networkAnalysis: "नेटवर्क विश्लेषण", connections: "संबंध", aiInvestigator: "एआई जांचकर्ता", investigatorAnalysis: "जांचकर्ता विश्लेषण", askAI: "एआई से पूछें", age: "आयु", closeFile: "फाइल बंद करें", addToList: "सूची में जोड़ें", removeFromList: "सूची से हटाएं", loading: "लोड हो रहा है…", loadingRecords: "रिकॉर्ड लोड हो रहे हैं…", noRecords: "डेटाबेस में कोई रिकॉर्ड नहीं मिला।", noSearchMatches: "इस खोज से कोई केस फाइल नहीं मिली।", searchResults: "फाइलें मिलीं", criminalsOnFile: "अपराधी रिकॉर्ड", basedIn: "स्थान", uploadAnalyze: "रिकॉर्ड अपलोड और विश्लेषण करें", recordSource: "रिकॉर्ड स्रोत", upload: "अपलोड", noDocuments: "अभी कोई दस्तावेज़ अपलोड नहीं है।", openOriginal: "मूल दस्तावेज़ खोलें", review: "समीक्षा", closeDocument: "दस्तावेज़ बंद करें", reset: "रीसेट", retry: "पुनः प्रयास", fit: "फिट", selectedPerson: "चयनित व्यक्ति", zoomIn: "ज़ूम इन", zoomOut: "ज़ूम आउट", map: "मानचित्र", network: "नेटवर्क", openFile: "फाइल खोलें", unpin: "पिन हटाएं", onTheList: "सूची में", noCases: "अभी कोई केस नहीं जोड़ा गया", tracked: "वर्तमान में ट्रैक किए गए अपराधी" },
};
Object.assign(messages.en, {
  activityEvidenceMismatch: "Needs review: this quote does not identify the linked person or entity. It cannot be relied on to support this connection.",
  activityInspectQuote: "Inspect original stored quote", activityProfileDetails: "Profile details from sources",
  connectedLocation: "Connected location", locationNotRecorded: "Not recorded",
  activityTitle: "Activity timeline", activityDescription: "Source records, newest recorded first. Recorded dates indicate when a source was added, not when the activity occurred.",
  activityRecorded: "Recorded", activitySource: "Source", activityEmpty: "No source activity has been recorded for this person.",
  activityError: "Could not load activity records.", activityCaseDate: "Case date", activityDateUnknown: "Date not recorded",
  activity_PERSON_RECORD: "Person recorded", activity_CONTACTED: "Contact recorded",
  activity_MENTIONED_IN: "Mentioned in case", activity_WITNESS_IN: "Witness in case", activity_SUSPECT_IN: "Suspect in case",
  activity_EMPLOYED_BY: "Employment recorded", activity_OWNS: "Ownership recorded",
  activity_RESIDES_IN: "Residence recorded", activity_SEEN_AT: "Sighting recorded",
  analysisIntro: "Search for people, add their networks, then select a node or relationship to investigate.",
  analysisFind: "Add a person to the workspace",
  analysisSearchHint: "Search by name, alias or ID — approximate spellings work too",
  analysisAdding: "Adding network…", analysisAdded: "Added", analysisAdd: "+ Add network",
  analysisCatalogError: "Unable to load the search records.", analysisGraphError: "Could not add this network. Select the search result to retry.",
  analysisNodes: "nodes", analysisLinks: "links", analysisRemove: "Remove network for",
  analysisStart: "Build your investigation workspace",
  analysisStartHint: "Search above and add one or more people. Shared records merge into a single relationship chart.",
  analysisClearChat: "Clear chat", analysisSelected: "Selected",
  analysisSelect: "Select a node or relationship in the chart to start.",
  analysisMessages: "Investigator conversation", analysisChatWelcome: "Explore the evidence",
  analysisChatHint: "Ask a focused question about the selected record and its connections. Each question uses that selection's source network.",
  analysisPrompt1: "How is this selection connected to the other people?",
  analysisPrompt2: "What does the available evidence tell us?",
  analysisYou: "You", analysisRetryQuestion: "Edit and retry",
  analysisQuestion: "Your question", analysisQuestionHint: "Ask about the selected evidence…",
  analysisEnterHint: "Enter to send · Shift + Enter for a new line",
  analysisThinking: "Thinking…", analysisReviewing: "Reviewing records…",
  analysisFailed: "Unable to generate an analysis. Please try again."
});
Object.assign(messages.hi, {
  activityEvidenceMismatch: "समीक्षा आवश्यक: इस उद्धरण में संबंधित व्यक्ति या इकाई की पहचान नहीं है। इसे इस संबंध का आधार नहीं माना जा सकता।",
  activityInspectQuote: "संग्रहीत मूल उद्धरण देखें", activityProfileDetails: "स्रोतों से प्रोफ़ाइल विवरण",
  connectedLocation: "संबंधित स्थान", locationNotRecorded: "दर्ज नहीं है",
  activityTitle: "गतिविधि समयरेखा", activityDescription: "स्रोत रिकॉर्ड, नवीनतम पहले। दर्ज तारीख स्रोत जोड़ने की है, गतिविधि होने की नहीं।",
  activityRecorded: "दर्ज", activitySource: "स्रोत", activityEmpty: "इस व्यक्ति की कोई स्रोत गतिविधि दर्ज नहीं है।",
  activityError: "गतिविधि रिकॉर्ड लोड नहीं हो सके।", activityCaseDate: "मामले की तारीख", activityDateUnknown: "तारीख दर्ज नहीं है",
  activity_PERSON_RECORD: "व्यक्ति का रिकॉर्ड", activity_CONTACTED: "संपर्क दर्ज",
  activity_MENTIONED_IN: "मामले में उल्लेख", activity_WITNESS_IN: "मामले में गवाह", activity_SUSPECT_IN: "मामले में संदिग्ध",
  activity_EMPLOYED_BY: "रोजगार दर्ज", activity_OWNS: "स्वामित्व दर्ज",
  activity_RESIDES_IN: "निवास दर्ज", activity_SEEN_AT: "देखे जाने का रिकॉर्ड",
  analysisIntro: "व्यक्तियों को खोजें, उनके नेटवर्क जोड़ें और जांच के लिए कोई नोड या संबंध चुनें।",
  analysisFind: "कार्यस्थान में व्यक्ति जोड़ें",
  analysisSearchHint: "नाम, उपनाम या आईडी खोजें — मिलती-जुलती वर्तनी भी चलेगी",
  analysisAdding: "नेटवर्क जोड़ रहे हैं…", analysisAdded: "जोड़ा गया", analysisAdd: "+ नेटवर्क जोड़ें",
  analysisCatalogError: "खोज के रिकॉर्ड लोड नहीं हो सके।", analysisGraphError: "नेटवर्क नहीं जुड़ सका। फिर प्रयास करने के लिए खोज परिणाम चुनें।",
  analysisNodes: "नोड", analysisLinks: "संबंध", analysisRemove: "इस व्यक्ति का नेटवर्क हटाएं:",
  analysisStart: "अपना जांच कार्यस्थान बनाएं",
  analysisStartHint: "ऊपर खोजकर एक या अधिक व्यक्ति जोड़ें। साझा रिकॉर्ड एक ही संबंध चार्ट में दिखाई देंगे।",
  analysisClearChat: "चैट साफ करें", analysisSelected: "चयनित",
  analysisSelect: "शुरू करने के लिए चार्ट में कोई नोड या संबंध चुनें।",
  analysisMessages: "जांचकर्ता की बातचीत", analysisChatWelcome: "साक्ष्यों की जांच करें",
  analysisChatHint: "चयनित रिकॉर्ड और उसके संबंधों पर प्रश्न पूछें। हर प्रश्न में उसी चयन के स्रोत नेटवर्क का उपयोग होता है।",
  analysisPrompt1: "यह चयन अन्य व्यक्तियों से कैसे जुड़ा है?",
  analysisPrompt2: "उपलब्ध साक्ष्य क्या बताते हैं?",
  analysisYou: "आप", analysisRetryQuestion: "बदलकर फिर पूछें",
  analysisQuestion: "आपका प्रश्न", analysisQuestionHint: "चयनित साक्ष्य के बारे में पूछें…",
  analysisEnterHint: "भेजें: Enter · नई पंक्ति: Shift + Enter",
  analysisThinking: "विचार कर रहे हैं…", analysisReviewing: "रिकॉर्ड की समीक्षा हो रही है…",
  analysisFailed: "विश्लेषण नहीं बन सका। कृपया फिर प्रयास करें।"
});
Object.assign(messages.en, {
  identityEyebrow: "Identity check", identityTitle: "Possible existing people", identityHint: "These names match existing records. A shared name does not prove the same person: compare the shared connections, cases and details before deciding.",
  identityUse: "Use existing person", identityAge: "Age", identityPlace: "Recorded place", identityCases: "Already in", identityNoCases: "No linked FIRs yet", identityRecordId: "Record ID", identityShared: "shared connections", identitySeparate: "Keep as a separate person",
  identityBack: "Back to review", identitySave: "Confirm identities and save", identitySaving: "Saving…"
});
Object.assign(messages.hi, {
  identityEyebrow: "पहचान जाँच", identityTitle: "संभावित मौजूदा व्यक्ति", identityHint: "ये नाम मौजूदा रिकॉर्ड से मेल खाते हैं। समान नाम से एक ही व्यक्ति सिद्ध नहीं होता: निर्णय लेने से पहले साझा संबंधों, मामलों और विवरणों की तुलना करें।",
  identityUse: "मौजूदा व्यक्ति का उपयोग करें", identityAge: "आयु", identityPlace: "दर्ज स्थान", identityCases: "पहले से शामिल", identityNoCases: "अभी कोई जुड़ी एफआईआर नहीं", identityRecordId: "रिकॉर्ड आईडी", identityShared: "साझा संबंध", identitySeparate: "अलग व्यक्ति के रूप में रखें",
  identityBack: "समीक्षा पर लौटें", identitySave: "पहचान की पुष्टि करें और सहेजें", identitySaving: "सहेज रहे हैं…"
});
Object.assign(messages.en, {
  recordTitle: "Detailed person record", recordDescription: "Stored identity, case, location and relationship information with source records. Missing details are not inferred.",
  recordDocuments: "source documents", recordEmbedded: "passages embedded", recordGenerate: "Generate detailed AI record", recordRegenerate: "Regenerate AI record",
  recordGenerating: "Generating…", recordWorking: "Retrieving evidence and writing the record…", recordAI: "AI-generated record", recordVerify: "Verify this generated record against the cited sources. Reported allegations are not established facts.",
  recordPartial: "The AI record covers a selection of sources. All stored details remain available below.", record_identity: "Identity and personal details", record_cases: "Case history and recorded offences",
  record_locations: "Addresses and connected locations", record_connections: "Recorded connections", record_sourceDetails: "Additional source details", recordNoDetails: "No information recorded in this category.",
  recordSources: "Source records and evidence", recordCharacters: "Source characters"
});
Object.assign(messages.hi, {
  recordTitle: "व्यक्ति का विस्तृत रिकॉर्ड", recordDescription: "पहचान, मामले, स्थान और संबंधों की दर्ज जानकारी तथा मूल स्रोत। अनुपलब्ध जानकारी का अनुमान नहीं लगाया जाता।",
  recordDocuments: "स्रोत दस्तावेज़", recordEmbedded: "अनुच्छेद एम्बेड किए गए", recordGenerate: "विस्तृत एआई रिकॉर्ड बनाएं", recordRegenerate: "एआई रिकॉर्ड फिर बनाएं",
  recordGenerating: "बना रहे हैं…", recordWorking: "साक्ष्य खोजकर रिकॉर्ड तैयार कर रहे हैं…", recordAI: "एआई द्वारा तैयार रिकॉर्ड", recordVerify: "इस रिकॉर्ड को दिए गए स्रोतों से सत्यापित करें। दर्ज आरोप सिद्ध तथ्य नहीं हैं।",
  recordPartial: "एआई रिकॉर्ड में चयनित स्रोत शामिल हैं। सभी दर्ज विवरण नीचे उपलब्ध हैं।", record_identity: "पहचान और व्यक्तिगत विवरण", record_cases: "मामलों का इतिहास और दर्ज अपराध",
  record_locations: "पते और संबंधित स्थान", record_connections: "दर्ज संबंध", record_sourceDetails: "स्रोतों के अतिरिक्त विवरण", recordNoDetails: "इस श्रेणी में कोई जानकारी दर्ज नहीं है।",
  recordSources: "स्रोत रिकॉर्ड और साक्ष्य", recordCharacters: "स्रोत अक्षर"
});
const LanguageContext = createContext(null);
export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => {
    const saved = localStorage.getItem("language") || localStorage.getItem("cna-language");
    return saved === "hi" || saved === "en" ? saved : "en";
  });
  const changeLanguage = (value) => { setLanguage(value); localStorage.setItem("language", value); localStorage.setItem("cna-language", value); document.documentElement.lang = value; };
  const value = useMemo(() => ({ language, setLanguage: changeLanguage, t: (key) => messages[language][key] || messages.en[key] || key }), [language]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}
export function useTranslation() { return useContext(LanguageContext) || { language: "en", setLanguage: () => {}, t: (key) => key }; }
