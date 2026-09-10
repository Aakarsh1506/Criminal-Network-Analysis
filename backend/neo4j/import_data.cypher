// =====================================================
// CRIMINAL NETWORK ANALYSIS SYSTEM
// Neo4j Data Import
// =====================================================

// -----------------------------------------------------
// 1. CRIME TYPES
// -----------------------------------------------------

UNWIND [
    {id: 1, name: "Robbery", description: "Theft involving force, threat, or intimidation."},
    {id: 2, name: "Fraud", description: "Deception or misrepresentation carried out for financial or personal gain."},
    {id: 3, name: "Extortion", description: "Obtaining money, property, or services through threats or coercion."},
    {id: 4, name: "Cybercrime", description: "Criminal activity involving computers, networks, or digital systems."},
    {id: 5, name: "Drug Trafficking", description: "Illegal distribution, transportation, or sale of controlled substances."},
    {id: 6, name: "Money Laundering", description: "Concealing the origins of illegally obtained money."},
    {id: 7, name: "Kidnapping", description: "Unlawfully taking or holding a person against their will."},
    {id: 8, name: "Burglary", description: "Unlawful entry into a building with intent to commit a crime."},
    {id: 9, name: "Assault", description: "Intentional physical attack or threat of physical harm."},
    {id: 10, name: "Homicide", description: "Unlawful killing of another person."}
] AS crime

MERGE (c:CrimeType {crime_id: crime.id})
SET c.crime_name = crime.name,
    c.description = crime.description;

// -----------------------------------------------------
// 2. LOCATIONS
// -----------------------------------------------------

UNWIND [
    {id: 1, city: "Mumbai", state: "Maharashtra", lat: 19.0760000, lon: 72.8777000},
    {id: 2, city: "New Delhi", state: "Delhi", lat: 28.6139000, lon: 77.2090000},
    {id: 3, city: "Bengaluru", state: "Karnataka", lat: 12.9716000, lon: 77.5946000},
    {id: 4, city: "Ahmedabad", state: "Gujarat", lat: 23.0225000, lon: 72.5714000},
    {id: 5, city: "Kolkata", state: "West Bengal", lat: 22.5726000, lon: 88.3639000},
    {id: 6, city: "Pune", state: "Maharashtra", lat: 18.5204000, lon: 73.8567000},
    {id: 7, city: "Jaipur", state: "Rajasthan", lat: 26.9124000, lon: 75.7873000},
    {id: 8, city: "Gurugram", state: "Haryana", lat: 28.4595000, lon: 77.0266000},
    {id: 9, city: "Kochi", state: "Kerala", lat: 9.9312000, lon: 76.2673000},
    {id: 10, city: "Hyderabad", state: "Telangana", lat: 17.3850000, lon: 78.4867000},
    {id: 11, city: "Lucknow", state: "Uttar Pradesh", lat: 26.8467000, lon: 80.9462000},
    {id: 12, city: "Patna", state: "Bihar", lat: 25.5941000, lon: 85.1376000},
    {id: 13, city: "Indore", state: "Madhya Pradesh", lat: 22.7196000, lon: 75.8577000},
    {id: 14, city: "Amritsar", state: "Punjab", lat: 31.6340000, lon: 74.8723000}
] AS location

MERGE (l:Location {location_id: location.id})
SET l.city = location.city,
    l.state = location.state,
    l.latitude = location.lat,
    l.longitude = location.lon;

// -----------------------------------------------------
// 3. PERSONS
// -----------------------------------------------------

UNWIND [
    {id:"P001", name:"Arjun Mehta", alias:"Shadow", dob:"1988-04-12", age:38, height:178, state:"Maharashtra", city:"Mumbai", last_seen:"2025-08-15", family:"Mother and younger brother", status:"Active"},
    {id:"P002", name:"Rohan Kapoor", alias:"Rex", dob:"1991-09-23", age:34, height:182, state:"Delhi", city:"New Delhi", last_seen:"2025-07-21", family:"Parents known", status:"Active"},
    {id:"P003", name:"Vikram Singh", alias:"Vicky", dob:"1985-01-17", age:41, height:175, state:"Karnataka", city:"Bengaluru", last_seen:"2025-06-12", family:"Wife and daughter", status:"Active"},
    {id:"P004", name:"Sameer Khan", alias:"Sam", dob:"1993-11-05", age:31, height:180, state:"Gujarat", city:"Ahmedabad", last_seen:"2025-08-02", family:"Father known", status:"Active"},
    {id:"P005", name:"Aditya Rao", alias:"Adi", dob:"1989-06-28", age:36, height:177, state:"West Bengal", city:"Kolkata", last_seen:"2025-05-19", family:"Parents known", status:"Under Investigation"},
    {id:"P006", name:"Karan Joshi", alias:"KJ", dob:"1995-03-14", age:30, height:174, state:"Maharashtra", city:"Pune", last_seen:"2025-08-10", family:"Mother known", status:"Active"},
    {id:"P007", name:"Nikhil Sharma", alias:"Nick", dob:"1987-12-02", age:38, height:181, state:"Rajasthan", city:"Jaipur", last_seen:"2025-04-25", family:"Brother known", status:"Active"},
    {id:"P008", name:"Manish Verma", alias:"Manu", dob:"1990-07-11", age:35, height:176, state:"Haryana", city:"Gurugram", last_seen:"2025-07-30", family:"Wife known", status:"Under Investigation"},
    {id:"P009", name:"Rahul Nair", alias:"RN", dob:"1992-02-26", age:34, height:179, state:"Kerala", city:"Kochi", last_seen:"2025-06-30", family:"Parents known", status:"Active"},
    {id:"P010", name:"Sahil Reddy", alias:"SR", dob:"1986-10-19", age:39, height:183, state:"Telangana", city:"Hyderabad", last_seen:"2025-08-05", family:"Sister known", status:"Active"},
    {id:"P011", name:"Dev Malhotra", alias:"Dev", dob:"1990-03-18", age:36, height:179, state:"Maharashtra", city:"Mumbai", last_seen:"2025-08-11", family:"Brother known", status:"Active"},
    {id:"P012", name:"Aman Gupta", alias:"Ace", dob:"1987-07-22", age:39, height:176, state:"Delhi", city:"New Delhi", last_seen:"2025-07-18", family:"Parents known", status:"Active"},
    {id:"P013", name:"Ravi Deshmukh", alias:"RDX", dob:"1992-11-09", age:33, height:181, state:"Maharashtra", city:"Pune", last_seen:"2025-06-27", family:"Mother known", status:"Under Investigation"},
    {id:"P014", name:"Imran Sheikh", alias:"Immy", dob:"1989-05-14", age:37, height:174, state:"Gujarat", city:"Ahmedabad", last_seen:"2025-08-03", family:"Wife known", status:"Active"},
    {id:"P015", name:"Suresh Iyer", alias:"Surya", dob:"1984-12-28", age:41, height:177, state:"Karnataka", city:"Bengaluru", last_seen:"2025-05-16", family:"Parents known", status:"Closed"},
    {id:"P016", name:"Rajiv Bansal", alias:"Raj", dob:"1993-02-06", age:33, height:183, state:"Haryana", city:"Gurugram", last_seen:"2025-07-29", family:"Brother known", status:"Active"},
    {id:"P017", name:"Mohit Chawla", alias:"MC", dob:"1988-08-19", age:38, height:180, state:"Rajasthan", city:"Jaipur", last_seen:"2025-04-21", family:"Father known", status:"Active"},
    {id:"P018", name:"Deepak Yadav", alias:"Deep", dob:"1991-10-31", age:34, height:175, state:"Uttar Pradesh", city:"Lucknow", last_seen:"2025-06-14", family:"Parents known", status:"Under Investigation"},
    {id:"P019", name:"Arman Qureshi", alias:"AQ", dob:"1994-04-25", age:32, height:178, state:"West Bengal", city:"Kolkata", last_seen:"2025-08-06", family:"Sister known", status:"Active"},
    {id:"P020", name:"Vivek Menon", alias:"VM", dob:"1986-09-13", age:39, height:182, state:"Kerala", city:"Kochi", last_seen:"2025-07-12", family:"Wife and son known", status:"Active"},
    {id:"P021", name:"Harsh Patel", alias:"HP", dob:"1990-01-29", age:36, height:177, state:"Gujarat", city:"Ahmedabad", last_seen:"2025-05-28", family:"Parents known", status:"Active"},
    {id:"P022", name:"Ankit Soni", alias:"AK", dob:"1995-06-17", age:31, height:173, state:"Maharashtra", city:"Mumbai", last_seen:"2025-08-14", family:"Mother known", status:"Under Investigation"},
    {id:"P023", name:"Manav Kapoor", alias:"MK", dob:"1985-03-07", age:41, height:180, state:"Delhi", city:"New Delhi", last_seen:"2025-06-03", family:"Wife known", status:"Active"},
    {id:"P024", name:"Tarun Reddy", alias:"TR", dob:"1992-09-26", age:33, height:184, state:"Telangana", city:"Hyderabad", last_seen:"2025-07-24", family:"Brother known", status:"Active"},
    {id:"P025", name:"Naveen Rao", alias:"Nav", dob:"1989-11-15", age:36, height:176, state:"Karnataka", city:"Bengaluru", last_seen:"2025-04-30", family:"Parents known", status:"Closed"},
    {id:"P026", name:"Yash Thakur", alias:"YT", dob:"1993-07-03", age:33, height:179, state:"Rajasthan", city:"Jaipur", last_seen:"2025-08-09", family:"Father known", status:"Active"},
    {id:"P027", name:"Faizan Ali", alias:"FZ", dob:"1987-02-21", age:39, height:175, state:"Maharashtra", city:"Pune", last_seen:"2025-06-22", family:"Mother and sister known", status:"Active"},
    {id:"P028", name:"Kunal Arora", alias:"KA", dob:"1991-05-30", age:35, height:181, state:"Haryana", city:"Gurugram", last_seen:"2025-07-07", family:"Parents known", status:"Under Investigation"},
    {id:"P029", name:"Ritesh Kumar", alias:"RK", dob:"1986-12-11", age:39, height:178, state:"Bihar", city:"Patna", last_seen:"2025-05-11", family:"Brother known", status:"Active"},
    {id:"P030", name:"Varun Nair", alias:"VN", dob:"1994-10-08", age:31, height:176, state:"Kerala", city:"Kochi", last_seen:"2025-08-12", family:"Parents known", status:"Active"},
    {id:"P031", name:"Abhishek Jain", alias:"AJ", dob:"1988-06-24", age:38, height:180, state:"Madhya Pradesh", city:"Indore", last_seen:"2025-06-19", family:"Wife known", status:"Active"},
    {id:"P032", name:"Siddharth Bose", alias:"Sid", dob:"1990-04-16", age:36, height:182, state:"West Bengal", city:"Kolkata", last_seen:"2025-07-15", family:"Parents known", status:"Under Investigation"},
    {id:"P033", name:"Raghav Mishra", alias:"RM", dob:"1985-08-27", age:41, height:177, state:"Uttar Pradesh", city:"Lucknow", last_seen:"2025-05-23", family:"Mother known", status:"Active"},
    {id:"P034", name:"Akash Kulkarni", alias:"AK", dob:"1992-01-12", age:34, height:179, state:"Maharashtra", city:"Pune", last_seen:"2025-08-07", family:"Parents known", status:"Active"},
    {id:"P035", name:"Shreyas Patil", alias:"SP", dob:"1989-09-05", age:37, height:181, state:"Maharashtra", city:"Mumbai", last_seen:"2025-06-29", family:"Brother known", status:"Closed"},
    {id:"P036", name:"Zaid Mirza", alias:"ZM", dob:"1993-03-23", age:33, height:175, state:"Telangana", city:"Hyderabad", last_seen:"2025-07-20", family:"Father known", status:"Active"},
    {id:"P037", name:"Rohit Agarwal", alias:"RA", dob:"1987-11-18", age:38, height:178, state:"Rajasthan", city:"Jaipur", last_seen:"2025-05-07", family:"Parents known", status:"Active"},
    {id:"P038", name:"Sameer Kulkarni", alias:"SK", dob:"1991-08-02", age:35, height:183, state:"Karnataka", city:"Bengaluru", last_seen:"2025-08-04", family:"Wife known", status:"Under Investigation"},
    {id:"P039", name:"Nitin Choudhary", alias:"NC", dob:"1986-05-26", age:40, height:176, state:"Haryana", city:"Gurugram", last_seen:"2025-06-11", family:"Brother known", status:"Active"},
    {id:"P040", name:"Aarav Shah", alias:"AS", dob:"1995-01-09", age:31, height:180, state:"Gujarat", city:"Ahmedabad", last_seen:"2025-07-31", family:"Parents known", status:"Active"},
    {id:"P041", name:"Ishaan Verma", alias:"IV", dob:"1990-10-17", age:35, height:174, state:"Uttar Pradesh", city:"Lucknow", last_seen:"2025-05-18", family:"Mother known", status:"Active"},
    {id:"P042", name:"Kabir Singh", alias:"KS", dob:"1984-07-29", age:42, height:182, state:"Punjab", city:"Amritsar", last_seen:"2025-06-26", family:"Wife and daughter known", status:"Under Investigation"},
    {id:"P043", name:"Vishal Mehra", alias:"VM", dob:"1989-02-14", age:37, height:179, state:"Maharashtra", city:"Mumbai", last_seen:"2025-08-13", family:"Parents known", status:"Active"},
    {id:"P044", name:"Sanjay Tiwari", alias:"ST", dob:"1988-12-03", age:37, height:177, state:"Madhya Pradesh", city:"Indore", last_seen:"2025-07-09", family:"Brother known", status:"Active"},
    {id:"P045", name:"Aryan Khanna", alias:"AK", dob:"1994-06-21", age:32, height:181, state:"Delhi", city:"New Delhi", last_seen:"2025-04-18", family:"Parents known", status:"Closed"},
    {id:"P046", name:"Rajat Sethi", alias:"RS", dob:"1987-04-05", age:39, height:178, state:"West Bengal", city:"Kolkata", last_seen:"2025-08-08", family:"Father known", status:"Active"},
    {id:"P047", name:"Neeraj Pillai", alias:"NP", dob:"1992-12-19", age:33, height:175, state:"Kerala", city:"Kochi", last_seen:"2025-06-05", family:"Parents known", status:"Under Investigation"},
    {id:"P048", name:"Kartik Joshi", alias:"KJ2", dob:"1990-07-13", age:36, height:180, state:"Maharashtra", city:"Pune", last_seen:"2025-07-27", family:"Sister known", status:"Active"},
    {id:"P049", name:"Devendra Rao", alias:"DR", dob:"1985-10-28", age:40, height:183, state:"Telangana", city:"Hyderabad", last_seen:"2025-05-14", family:"Wife known", status:"Active"},
    {id:"P050", name:"Amit Solanki", alias:"AS2", dob:"1993-05-08", age:33, height:176, state:"Gujarat", city:"Ahmedabad", last_seen:"2025-08-10", family:"Parents known", status:"Active"}
] AS person

MERGE (p:Person {person_id: person.id})
SET p.name = person.name,
    p.alias = person.alias,
    p.dob = date(person.dob),
    p.age = person.age,
    p.height_cm = person.height,
    p.state = person.state,
    p.city = person.city,
    p.last_seen = date(person.last_seen),
    p.family_known = person.family,
    p.record_status = person.status;

// -----------------------------------------------------
// 4. CASES
// -----------------------------------------------------

UNWIND [
    {case_id:"C058", person_id:"P043", crime_id:1, case_month:"2025-08-01", location_name:"Mumbai", case_status:"Open", location_id:1},
    {case_id:"C050", person_id:"P035", crime_id:3, case_month:"2025-08-09", location_name:"Mumbai", case_status:"Open", location_id:1},
    {case_id:"C037", person_id:"P022", crime_id:1, case_month:"2025-03-07", location_name:"Mumbai", case_status:"Under Investigation", location_id:1},
    {case_id:"C017", person_id:"P011", crime_id:6, case_month:"2025-04-08", location_name:"Mumbai", case_status:"Under Investigation", location_id:1},
    {case_id:"C016", person_id:"P011", crime_id:2, case_month:"2025-01-12", location_name:"Mumbai", case_status:"Open", location_id:1},
    {case_id:"C015", person_id:"P001", crime_id:4, case_month:"2025-08-01", location_name:"Mumbai", case_status:"Open", location_id:1},
    {case_id:"C002", person_id:"P001", crime_id:3, case_month:"2025-03-20", location_name:"Mumbai", case_status:"Under Investigation", location_id:1},
    {case_id:"C001", person_id:"P001", crime_id:1, case_month:"2025-01-15", location_name:"Mumbai", case_status:"Open", location_id:1},

    {case_id:"C060", person_id:"P045", crime_id:4, case_month:"2025-08-11", location_name:"New Delhi", case_status:"Open", location_id:2},
    {case_id:"C038", person_id:"P023", crime_id:6, case_month:"2025-04-19", location_name:"New Delhi", case_status:"Open", location_id:2},
    {case_id:"C019", person_id:"P012", crime_id:3, case_month:"2025-06-14", location_name:"New Delhi", case_status:"Closed", location_id:2},
    {case_id:"C018", person_id:"P012", crime_id:4, case_month:"2025-02-19", location_name:"New Delhi", case_status:"Open", location_id:2},
    {case_id:"C004", person_id:"P002", crime_id:4, case_month:"2025-05-18", location_name:"New Delhi", case_status:"Open", location_id:2},
    {case_id:"C003", person_id:"P002", crime_id:2, case_month:"2025-02-10", location_name:"New Delhi", case_status:"Closed", location_id:2},

    {case_id:"C053", person_id:"P038", crime_id:4, case_month:"2025-03-15", location_name:"Bengaluru", case_status:"Closed", location_id:3},
    {case_id:"C040", person_id:"P025", crime_id:5, case_month:"2025-06-15", location_name:"Bengaluru", case_status:"Open", location_id:3},
    {case_id:"C025", person_id:"P015", crime_id:4, case_month:"2025-06-22", location_name:"Bengaluru", case_status:"Open", location_id:3},
    {case_id:"C024", person_id:"P015", crime_id:6, case_month:"2025-02-08", location_name:"Bengaluru", case_status:"Under Investigation", location_id:3},
    {case_id:"C006", person_id:"P003", crime_id:6, case_month:"2025-04-12", location_name:"Bengaluru", case_status:"Open", location_id:3},
    {case_id:"C005", person_id:"P003", crime_id:5, case_month:"2025-01-25", location_name:"Bengaluru", case_status:"Under Investigation", location_id:3},

    {case_id:"C065", person_id:"P050", crime_id:2, case_month:"2025-07-23", location_name:"Ahmedabad", case_status:"Closed", location_id:4},
    {case_id:"C055", person_id:"P040", crime_id:9, case_month:"2025-05-17", location_name:"Ahmedabad", case_status:"Under Investigation", location_id:4},
    {case_id:"C036", person_id:"P021", crime_id:9, case_month:"2025-02-11", location_name:"Ahmedabad", case_status:"Open", location_id:4},
    {case_id:"C023", person_id:"P014", crime_id:9, case_month:"2025-05-16", location_name:"Ahmedabad", case_status:"Closed", location_id:4},
    {case_id:"C022", person_id:"P014", crime_id:3, case_month:"2025-01-27", location_name:"Ahmedabad", case_status:"Open", location_id:4},
    {case_id:"C007", person_id:"P004", crime_id:2, case_month:"2025-06-08", location_name:"Ahmedabad", case_status:"Closed", location_id:4},

    {case_id:"C061", person_id:"P046", crime_id:3, case_month:"2025-03-12", location_name:"Kolkata", case_status:"Closed", location_id:5},
    {case_id:"C047", person_id:"P032", crime_id:4, case_month:"2025-06-18", location_name:"Kolkata", case_status:"Under Investigation", location_id:5},
    {case_id:"C033", person_id:"P019", crime_id:6, case_month:"2025-07-18", location_name:"Kolkata", case_status:"Under Investigation", location_id:5},
    {case_id:"C032", person_id:"P019", crime_id:3, case_month:"2025-03-21", location_name:"Kolkata", case_status:"Open", location_id:5},
    {case_id:"C008", person_id:"P005", crime_id:7, case_month:"2025-02-14", location_name:"Kolkata", case_status:"Open", location_id:5},

    {case_id:"C063", person_id:"P048", crime_id:8, case_month:"2025-05-21", location_name:"Pune", case_status:"Under Investigation", location_id:6},
    {case_id:"C049", person_id:"P034", crime_id:1, case_month:"2025-08-03", location_name:"Pune", case_status:"Closed", location_id:6},
    {case_id:"C042", person_id:"P027", crime_id:2, case_month:"2025-01-22", location_name:"Pune", case_status:"Open", location_id:6},
    {case_id:"C021", person_id:"P013", crime_id:5, case_month:"2025-07-11", location_name:"Pune", case_status:"Under Investigation", location_id:6},
    {case_id:"C020", person_id:"P013", crime_id:1, case_month:"2025-03-05", location_name:"Pune", case_status:"Open", location_id:6},
    {case_id:"C010", person_id:"P006", crime_id:1, case_month:"2025-07-22", location_name:"Pune", case_status:"Open", location_id:6},
    {case_id:"C009", person_id:"P006", crime_id:8, case_month:"2025-03-11", location_name:"Pune", case_status:"Closed", location_id:6},

    {case_id:"C052", person_id:"P037", crime_id:8, case_month:"2025-02-24", location_name:"Jaipur", case_status:"Open", location_id:7},
    {case_id:"C041", person_id:"P026", crime_id:8, case_month:"2025-07-08", location_name:"Jaipur", case_status:"Closed", location_id:7},
    {case_id:"C029", person_id:"P017", crime_id:8, case_month:"2025-04-25", location_name:"Jaipur", case_status:"Closed", location_id:7},
    {case_id:"C028", person_id:"P017", crime_id:1, case_month:"2025-01-31", location_name:"Jaipur", case_status:"Open", location_id:7},
    {case_id:"C011", person_id:"P007", crime_id:9, case_month:"2025-04-17", location_name:"Jaipur", case_status:"Under Investigation", location_id:7},

    {case_id:"C054", person_id:"P039", crime_id:6, case_month:"2025-04-21", location_name:"Gurugram", case_status:"Open", location_id:8},
    {case_id:"C043", person_id:"P028", crime_id:3, case_month:"2025-02-17", location_name:"Gurugram", case_status:"Under Investigation", location_id:8},
    {case_id:"C027", person_id:"P016", crime_id:10, case_month:"2025-07-04", location_name:"Gurugram", case_status:"Open", location_id:8},
    {case_id:"C026", person_id:"P016", crime_id:2, case_month:"2025-03-18", location_name:"Gurugram", case_status:"Closed", location_id:8},
    {case_id:"C012", person_id:"P008", crime_id:4, case_month:"2025-05-29", location_name:"Gurugram", case_status:"Open", location_id:8},

    {case_id:"C062", person_id:"P047", crime_id:6, case_month:"2025-04-16", location_name:"Kochi", case_status:"Open", location_id:9},
    {case_id:"C045", person_id:"P030", crime_id:9, case_month:"2025-04-13", location_name:"Kochi", case_status:"Closed", location_id:9},
    {case_id:"C035", person_id:"P020", crime_id:2, case_month:"2025-05-29", location_name:"Kochi", case_status:"Open", location_id:9},
    {case_id:"C034", person_id:"P020", crime_id:4, case_month:"2025-01-16", location_name:"Kochi", case_status:"Closed", location_id:9},
    {case_id:"C013", person_id:"P009", crime_id:5, case_month:"2025-06-16", location_name:"Kochi", case_status:"Closed", location_id:9},

    {case_id:"C064", person_id:"P049", crime_id:5, case_month:"2025-06-28", location_name:"Hyderabad", case_status:"Open", location_id:10},
    {case_id:"C051", person_id:"P036", crime_id:2, case_month:"2025-01-29", location_name:"Hyderabad", case_status:"Under Investigation", location_id:10},
    {case_id:"C039", person_id:"P024", crime_id:4, case_month:"2025-05-23", location_name:"Hyderabad", case_status:"Closed", location_id:10},
    {case_id:"C014", person_id:"P010", crime_id:6, case_month:"2025-07-05", location_name:"Hyderabad", case_status:"Under Investigation", location_id:10},

    {case_id:"C056", person_id:"P041", crime_id:5, case_month:"2025-06-06", location_name:"Lucknow", case_status:"Open", location_id:11},
    {case_id:"C048", person_id:"P033", crime_id:5, case_month:"2025-07-12", location_name:"Lucknow", case_status:"Open", location_id:11},
    {case_id:"C031", person_id:"P018", crime_id:7, case_month:"2025-06-09", location_name:"Lucknow", case_status:"Open", location_id:11},
    {case_id:"C030", person_id:"P018", crime_id:5, case_month:"2025-02-14", location_name:"Lucknow", case_status:"Under Investigation", location_id:11},

    {case_id:"C044", person_id:"P029", crime_id:7, case_month:"2025-03-26", location_name:"Patna", case_status:"Open", location_id:12},

    {case_id:"C059", person_id:"P044", crime_id:2, case_month:"2025-08-06", location_name:"Indore", case_status:"Under Investigation", location_id:13},
    {case_id:"C046", person_id:"P031", crime_id:6, case_month:"2025-05-05", location_name:"Indore", case_status:"Open", location_id:13},

    {case_id:"C057", person_id:"P042", crime_id:7, case_month:"2025-07-19", location_name:"Amritsar", case_status:"Closed", location_id:14}
] AS row

MERGE (c:Case {case_id: row.case_id})
SET c.case_month = date(row.case_month),
    c.location_name = row.location_name,
    c.case_status = row.case_status,

  
    c.person_id = row.person_id,
    c.crime_id = row.crime_id,
    c.location_id = row.location_id;

    // -----------------------------------------------------
// 5. RELATIONSHIPS
// -----------------------------------------------------

// Person -> Case
MATCH (c:Case)
MATCH (p:Person {person_id: c.person_id})
MERGE (p)-[:INVOLVED_IN]->(c);

// Case -> CrimeType
MATCH (c:Case)
MATCH (crime:CrimeType {crime_id: c.crime_id})
MERGE (c)-[:OF_TYPE]->(crime);

// Case -> Location
MATCH (c:Case)
MATCH (l:Location {location_id: c.location_id})
MERGE (c)-[:OCCURRED_AT]->(l);