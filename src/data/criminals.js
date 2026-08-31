// Fake hardcoded criminal database — replace with real API/DB later

export const presetTags = [
  "Murder",
  "Theft",
  "Robbery",
  "Extortion",
  "Cybercrime",
  "Fraud",
  "Smuggling",
  "Kidnapping",
];

export const criminalsDB = [
  {
    id: 1,
    name: "Rajesh Verma",
    alias: "Tiger",
    dob: "1985-04-12",
    age: 41,
    height: "5'11\"",
    location: { city: "Mumbai", x: 22, y: 62 },
    lastSeen: "Dharavi, Mumbai — 14 Aug 2026",
    crimeTags: ["Murder", "Extortion"],
    family: [
      { name: "Sunita Verma", age: 38, relation: "Wife" },
      { name: "Rohan Verma", age: 15, relation: "Son" },
    ],
    photo: "https://ui-avatars.com/api/?name=Rajesh+Verma&background=8B0000&color=fff&size=200&bold=true",
  },
  {
    id: 2,
    name: "Vikram Singh",
    alias: "Bulldozer",
    dob: "1990-09-03",
    age: 35,
    height: "6'1\"",
    location: { city: "Delhi", x: 42, y: 24 },
    lastSeen: "Karol Bagh, Delhi — 20 Aug 2026",
    crimeTags: ["Theft", "Robbery"],
    family: [
      { name: "Meena Singh", age: 60, relation: "Mother" },
    ],
    photo: "https://ui-avatars.com/api/?name=Vikram+Singh&background=1B4332&color=fff&size=200&bold=true",
  },
  {
    id: 3,
    name: "Arjun Malhotra",
    alias: "Ghost",
    dob: "1993-01-27",
    age: 33,
    height: "5'9\"",
    location: { city: "Bangalore", x: 36, y: 76 },
    lastSeen: "Koramangala, Bangalore — 10 Aug 2026",
    crimeTags: ["Cybercrime", "Fraud"],
    family: [
      { name: "Priya Malhotra", age: 30, relation: "Sister" },
    ],
    photo: "https://ui-avatars.com/api/?name=Arjun+Malhotra&background=1E3A8A&color=fff&size=200&bold=true",
  },
  {
    id: 4,
    name: "Suresh Yadav",
    alias: "Python",
    dob: "1980-06-15",
    age: 46,
    height: "5'8\"",
    location: { city: "Kolkata", x: 71, y: 46 },
    lastSeen: "Howrah, Kolkata — 5 Aug 2026",
    crimeTags: ["Smuggling", "Murder"],
    family: [
      { name: "Kavita Yadav", age: 44, relation: "Wife" },
      { name: "Aditya Yadav", age: 20, relation: "Son" },
    ],
    photo: "https://ui-avatars.com/api/?name=Suresh+Yadav&background=4A044E&color=fff&size=200&bold=true",
  },
  {
    id: 5,
    name: "Amit Sharma",
    alias: "Shadow",
    dob: "1997-11-09",
    age: 28,
    height: "5'10\"",
    location: { city: "Chennai", x: 46, y: 82 },
    lastSeen: "T. Nagar, Chennai — 22 Aug 2026",
    crimeTags: ["Theft"],
    family: [
      { name: "Lakshmi Sharma", age: 55, relation: "Mother" },
    ],
    photo: "https://ui-avatars.com/api/?name=Amit+Sharma&background=713F12&color=fff&size=200&bold=true",
  },
];

// criminal-to-criminal relations, used to draw the relationship map
export const relationsDB = [
  { from: 1, to: 2, type: "Associate" },
  { from: 1, to: 3, type: "Financier" },
  { from: 2, to: 4, type: "Weapons Supplier" },
  { from: 3, to: 5, type: "Recruiter" },
  { from: 4, to: 5, type: "Smuggling Partner" },
];

export function getCriminalById(id) {
  return criminalsDB.find((c) => c.id === Number(id));
}

export function getRelationsForCriminal(id) {
  const numId = Number(id);
  return relationsDB
    .filter((r) => r.from === numId || r.to === numId)
    .map((r) => {
      const relatedId = r.from === numId ? r.to : r.from;
      return { criminal: getCriminalById(relatedId), type: r.type };
    })
    .filter((r) => r.criminal);
}