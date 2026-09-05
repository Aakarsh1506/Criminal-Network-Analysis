--
-- PostgreSQL database dump
--

\restrict FdNCXUVUdDbakaX7DJfgiyXNY2uFLkeaA0hpf9hzox0VWXdjXeSxkVuYLb7gUbu

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

-- Started on 2026-09-05 15:27:22

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 2 (class 3079 OID 24577)
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- TOC entry 5963 (class 0 OID 0)
-- Dependencies: 2
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 228 (class 1259 OID 25689)
-- Name: cases; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cases (
    case_id character varying(20) NOT NULL,
    person_id character varying(20) NOT NULL,
    crime_id integer,
    case_month date,
    location_name character varying(150),
    case_status character varying(100),
    location_id integer
);


ALTER TABLE public.cases OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 25676)
-- Name: crime_types; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.crime_types (
    crime_id integer NOT NULL,
    crime_name character varying(100) NOT NULL,
    description text
);


ALTER TABLE public.crime_types OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 25675)
-- Name: crime_types_crime_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.crime_types_crime_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.crime_types_crime_id_seq OWNER TO postgres;

--
-- TOC entry 5964 (class 0 OID 0)
-- Dependencies: 226
-- Name: crime_types_crime_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.crime_types_crime_id_seq OWNED BY public.crime_types.crime_id;


--
-- TOC entry 230 (class 1259 OID 25707)
-- Name: locations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.locations (
    location_id integer NOT NULL,
    city character varying(100) NOT NULL,
    state character varying(100) NOT NULL,
    latitude numeric(10,7),
    longitude numeric(10,7),
    geom public.geometry(Point,4326)
);


ALTER TABLE public.locations OWNER TO postgres;

--
-- TOC entry 229 (class 1259 OID 25706)
-- Name: locations_location_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.locations_location_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.locations_location_id_seq OWNER TO postgres;

--
-- TOC entry 5965 (class 0 OID 0)
-- Dependencies: 229
-- Name: locations_location_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.locations_location_id_seq OWNED BY public.locations.location_id;


--
-- TOC entry 225 (class 1259 OID 25665)
-- Name: persons; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.persons (
    person_id character varying(20) NOT NULL,
    name character varying(100) NOT NULL,
    alias character varying(100),
    dob date,
    age integer,
    height_cm integer,
    state character varying(100),
    city character varying(100),
    last_seen date,
    family_known text,
    photo character varying(255),
    record_status character varying(100) NOT NULL
);


ALTER TABLE public.persons OWNER TO postgres;

--
-- TOC entry 5782 (class 2604 OID 25679)
-- Name: crime_types crime_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crime_types ALTER COLUMN crime_id SET DEFAULT nextval('public.crime_types_crime_id_seq'::regclass);


--
-- TOC entry 5783 (class 2604 OID 25710)
-- Name: locations location_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.locations ALTER COLUMN location_id SET DEFAULT nextval('public.locations_location_id_seq'::regclass);


--
-- TOC entry 5955 (class 0 OID 25689)
-- Dependencies: 228
-- Data for Name: cases; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.cases (case_id, person_id, crime_id, case_month, location_name, case_status, location_id) FROM stdin;
C058	P043	1	2025-08-01	Mumbai	Open	1
C050	P035	3	2025-08-09	Mumbai	Open	1
C037	P022	1	2025-03-07	Mumbai	Under Investigation	1
C017	P011	6	2025-04-08	Mumbai	Under Investigation	1
C016	P011	2	2025-01-12	Mumbai	Open	1
C015	P001	4	2025-08-01	Mumbai	Open	1
C002	P001	3	2025-03-20	Mumbai	Under Investigation	1
C001	P001	1	2025-01-15	Mumbai	Open	1
C060	P045	4	2025-08-11	New Delhi	Open	2
C038	P023	6	2025-04-19	New Delhi	Open	2
C019	P012	3	2025-06-14	New Delhi	Closed	2
C018	P012	4	2025-02-19	New Delhi	Open	2
C004	P002	4	2025-05-18	New Delhi	Open	2
C003	P002	2	2025-02-10	New Delhi	Closed	2
C053	P038	4	2025-03-15	Bengaluru	Closed	3
C040	P025	5	2025-06-15	Bengaluru	Open	3
C025	P015	4	2025-06-22	Bengaluru	Open	3
C024	P015	6	2025-02-08	Bengaluru	Under Investigation	3
C006	P003	6	2025-04-12	Bengaluru	Open	3
C005	P003	5	2025-01-25	Bengaluru	Under Investigation	3
C065	P050	2	2025-07-23	Ahmedabad	Closed	4
C055	P040	9	2025-05-17	Ahmedabad	Under Investigation	4
C036	P021	9	2025-02-11	Ahmedabad	Open	4
C023	P014	9	2025-05-16	Ahmedabad	Closed	4
C022	P014	3	2025-01-27	Ahmedabad	Open	4
C007	P004	2	2025-06-08	Ahmedabad	Closed	4
C061	P046	3	2025-03-12	Kolkata	Closed	5
C047	P032	4	2025-06-18	Kolkata	Under Investigation	5
C033	P019	6	2025-07-18	Kolkata	Under Investigation	5
C032	P019	3	2025-03-21	Kolkata	Open	5
C008	P005	7	2025-02-14	Kolkata	Open	5
C063	P048	8	2025-05-21	Pune	Under Investigation	6
C049	P034	1	2025-08-03	Pune	Closed	6
C042	P027	2	2025-01-22	Pune	Open	6
C021	P013	5	2025-07-11	Pune	Under Investigation	6
C020	P013	1	2025-03-05	Pune	Open	6
C010	P006	1	2025-07-22	Pune	Open	6
C009	P006	8	2025-03-11	Pune	Closed	6
C052	P037	8	2025-02-24	Jaipur	Open	7
C041	P026	8	2025-07-08	Jaipur	Closed	7
C029	P017	8	2025-04-25	Jaipur	Closed	7
C028	P017	1	2025-01-31	Jaipur	Open	7
C011	P007	9	2025-04-17	Jaipur	Under Investigation	7
C054	P039	6	2025-04-21	Gurugram	Open	8
C043	P028	3	2025-02-17	Gurugram	Under Investigation	8
C027	P016	10	2025-07-04	Gurugram	Open	8
C026	P016	2	2025-03-18	Gurugram	Closed	8
C012	P008	4	2025-05-29	Gurugram	Open	8
C062	P047	6	2025-04-16	Kochi	Open	9
C045	P030	9	2025-04-13	Kochi	Closed	9
C035	P020	2	2025-05-29	Kochi	Open	9
C034	P020	4	2025-01-16	Kochi	Closed	9
C013	P009	5	2025-06-16	Kochi	Closed	9
C064	P049	5	2025-06-28	Hyderabad	Open	10
C051	P036	2	2025-01-29	Hyderabad	Under Investigation	10
C039	P024	4	2025-05-23	Hyderabad	Closed	10
C014	P010	6	2025-07-05	Hyderabad	Under Investigation	10
C056	P041	5	2025-06-06	Lucknow	Open	11
C048	P033	5	2025-07-12	Lucknow	Open	11
C031	P018	7	2025-06-09	Lucknow	Open	11
C030	P018	5	2025-02-14	Lucknow	Under Investigation	11
C044	P029	7	2025-03-26	Patna	Open	12
C059	P044	2	2025-08-06	Indore	Under Investigation	13
C046	P031	6	2025-05-05	Indore	Open	13
C057	P042	7	2025-07-19	Amritsar	Closed	14
\.


--
-- TOC entry 5954 (class 0 OID 25676)
-- Dependencies: 227
-- Data for Name: crime_types; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.crime_types (crime_id, crime_name, description) FROM stdin;
1	Robbery	Theft involving force, threat, or intimidation.
2	Fraud	Deception or misrepresentation carried out for financial or personal gain.
3	Extortion	Obtaining money, property, or services through threats or coercion.
4	Cybercrime	Criminal activity involving computers, networks, or digital systems.
5	Drug Trafficking	Illegal distribution, transportation, or sale of controlled substances.
6	Money Laundering	Concealing the origins of illegally obtained money.
7	Kidnapping	Unlawfully taking or holding a person against their will.
8	Burglary	Unlawful entry into a building with intent to commit a crime.
9	Assault	Intentional physical attack or threat of physical harm.
10	Homicide	Unlawful killing of another person.
\.


--
-- TOC entry 5957 (class 0 OID 25707)
-- Dependencies: 230
-- Data for Name: locations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.locations (location_id, city, state, latitude, longitude, geom) FROM stdin;
1	Mumbai	Maharashtra	19.0760000	72.8777000	0101000020E6100000C0EC9E3C2C385240FA7E6ABC74133340
2	New Delhi	Delhi	28.6139000	77.2090000	0101000020E61000004C378941604D5340B003E78C289D3C40
3	Bengaluru	Karnataka	12.9716000	77.5946000	0101000020E6100000E78C28ED0D6653405396218E75F12940
4	Ahmedabad	Gujarat	23.0225000	72.5714000	0101000020E6100000CD3B4ED191245240F6285C8FC2053740
5	Kolkata	West Bengal	22.5726000	88.3639000	0101000020E6100000ECC039234A1756408AB0E1E995923640
6	Pune	Maharashtra	18.5204000	73.8567000	0101000020E6100000ED9E3C2CD4765240A1D634EF38853240
7	Jaipur	Rajasthan	26.9124000	75.7873000	0101000020E610000003098A1F63F25240D3DEE00B93E93A40
8	Gurugram	Haryana	28.4595000	77.0266000	0101000020E6100000B6847CD0B34153401283C0CAA1753C40
9	Kochi	Kerala	9.9312000	76.2673000	0101000020E6100000228E75711B1153400612143FC6DC2340
10	Hyderabad	Telangana	17.3850000	78.4867000	0101000020E6100000A5BDC117269F5340C3F5285C8F623140
11	Lucknow	Uttar Pradesh	26.8467000	80.9462000	0101000020E61000006ADE718A8E3C5440F085C954C1D83A40
12	Patna	Bihar	25.5941000	85.1376000	0101000020E61000007FFB3A70CE485540B98D06F016983940
13	Indore	Madhya Pradesh	22.7196000	75.8577000	0101000020E6100000DE718A8EE4F652409C33A2B437B83640
14	Amritsar	Punjab	31.6340000	74.8723000	0101000020E6100000401361C3D3B75240FCA9F1D24DA23F40
\.


--
-- TOC entry 5952 (class 0 OID 25665)
-- Dependencies: 225
-- Data for Name: persons; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.persons (person_id, name, alias, dob, age, height_cm, state, city, last_seen, family_known, photo, record_status) FROM stdin;
P001	Arjun Mehta	Shadow	1988-04-12	38	178	Maharashtra	Mumbai	2025-08-15	Mother and younger brother	\N	Active
P002	Rohan Kapoor	Rex	1991-09-23	34	182	Delhi	New Delhi	2025-07-21	Parents known	\N	Active
P003	Vikram Singh	Vicky	1985-01-17	41	175	Karnataka	Bengaluru	2025-06-12	Wife and daughter	\N	Active
P004	Sameer Khan	Sam	1993-11-05	31	180	Gujarat	Ahmedabad	2025-08-02	Father known	\N	Active
P005	Aditya Rao	Adi	1989-06-28	36	177	West Bengal	Kolkata	2025-05-19	Parents known	\N	Under Investigation
P006	Karan Joshi	KJ	1995-03-14	30	174	Maharashtra	Pune	2025-08-10	Mother known	\N	Active
P007	Nikhil Sharma	Nick	1987-12-02	38	181	Rajasthan	Jaipur	2025-04-25	Brother known	\N	Active
P008	Manish Verma	Manu	1990-07-11	35	176	Haryana	Gurugram	2025-07-30	Wife known	\N	Under Investigation
P009	Rahul Nair	RN	1992-02-26	34	179	Kerala	Kochi	2025-06-30	Parents known	\N	Active
P010	Sahil Reddy	SR	1986-10-19	39	183	Telangana	Hyderabad	2025-08-05	Sister known	\N	Active
P011	Dev Malhotra	Dev	1990-03-18	36	179	Maharashtra	Mumbai	2025-08-11	Brother known	\N	Active
P012	Aman Gupta	Ace	1987-07-22	39	176	Delhi	New Delhi	2025-07-18	Parents known	\N	Active
P013	Ravi Deshmukh	RDX	1992-11-09	33	181	Maharashtra	Pune	2025-06-27	Mother known	\N	Under Investigation
P014	Imran Sheikh	Immy	1989-05-14	37	174	Gujarat	Ahmedabad	2025-08-03	Wife known	\N	Active
P015	Suresh Iyer	Surya	1984-12-28	41	177	Karnataka	Bengaluru	2025-05-16	Parents known	\N	Closed
P016	Rajiv Bansal	Raj	1993-02-06	33	183	Haryana	Gurugram	2025-07-29	Brother known	\N	Active
P017	Mohit Chawla	MC	1988-08-19	38	180	Rajasthan	Jaipur	2025-04-21	Father known	\N	Active
P018	Deepak Yadav	Deep	1991-10-31	34	175	Uttar Pradesh	Lucknow	2025-06-14	Parents known	\N	Under Investigation
P019	Arman Qureshi	AQ	1994-04-25	32	178	West Bengal	Kolkata	2025-08-06	Sister known	\N	Active
P020	Vivek Menon	VM	1986-09-13	39	182	Kerala	Kochi	2025-07-12	Wife and son known	\N	Active
P021	Harsh Patel	HP	1990-01-29	36	177	Gujarat	Ahmedabad	2025-05-28	Parents known	\N	Active
P022	Ankit Soni	AK	1995-06-17	31	173	Maharashtra	Mumbai	2025-08-14	Mother known	\N	Under Investigation
P023	Manav Kapoor	MK	1985-03-07	41	180	Delhi	New Delhi	2025-06-03	Wife known	\N	Active
P024	Tarun Reddy	TR	1992-09-26	33	184	Telangana	Hyderabad	2025-07-24	Brother known	\N	Active
P025	Naveen Rao	Nav	1989-11-15	36	176	Karnataka	Bengaluru	2025-04-30	Parents known	\N	Closed
P026	Yash Thakur	YT	1993-07-03	33	179	Rajasthan	Jaipur	2025-08-09	Father known	\N	Active
P027	Faizan Ali	FZ	1987-02-21	39	175	Maharashtra	Pune	2025-06-22	Mother and sister known	\N	Active
P028	Kunal Arora	KA	1991-05-30	35	181	Haryana	Gurugram	2025-07-07	Parents known	\N	Under Investigation
P029	Ritesh Kumar	RK	1986-12-11	39	178	Bihar	Patna	2025-05-11	Brother known	\N	Active
P030	Varun Nair	VN	1994-10-08	31	176	Kerala	Kochi	2025-08-12	Parents known	\N	Active
P031	Abhishek Jain	AJ	1988-06-24	38	180	Madhya Pradesh	Indore	2025-06-19	Wife known	\N	Active
P032	Siddharth Bose	Sid	1990-04-16	36	182	West Bengal	Kolkata	2025-07-15	Parents known	\N	Under Investigation
P033	Raghav Mishra	RM	1985-08-27	41	177	Uttar Pradesh	Lucknow	2025-05-23	Mother known	\N	Active
P034	Akash Kulkarni	AK	1992-01-12	34	179	Maharashtra	Pune	2025-08-07	Parents known	\N	Active
P035	Shreyas Patil	SP	1989-09-05	37	181	Maharashtra	Mumbai	2025-06-29	Brother known	\N	Closed
P036	Zaid Mirza	ZM	1993-03-23	33	175	Telangana	Hyderabad	2025-07-20	Father known	\N	Active
P037	Rohit Agarwal	RA	1987-11-18	38	178	Rajasthan	Jaipur	2025-05-07	Parents known	\N	Active
P038	Sameer Kulkarni	SK	1991-08-02	35	183	Karnataka	Bengaluru	2025-08-04	Wife known	\N	Under Investigation
P039	Nitin Choudhary	NC	1986-05-26	40	176	Haryana	Gurugram	2025-06-11	Brother known	\N	Active
P040	Aarav Shah	AS	1995-01-09	31	180	Gujarat	Ahmedabad	2025-07-31	Parents known	\N	Active
P041	Ishaan Verma	IV	1990-10-17	35	174	Uttar Pradesh	Lucknow	2025-05-18	Mother known	\N	Active
P042	Kabir Singh	KS	1984-07-29	42	182	Punjab	Amritsar	2025-06-26	Wife and daughter known	\N	Under Investigation
P043	Vishal Mehra	VM	1989-02-14	37	179	Maharashtra	Mumbai	2025-08-13	Parents known	\N	Active
P044	Sanjay Tiwari	ST	1988-12-03	37	177	Madhya Pradesh	Indore	2025-07-09	Brother known	\N	Active
P045	Aryan Khanna	AK	1994-06-21	32	181	Delhi	New Delhi	2025-04-18	Parents known	\N	Closed
P046	Rajat Sethi	RS	1987-04-05	39	178	West Bengal	Kolkata	2025-08-08	Father known	\N	Active
P047	Neeraj Pillai	NP	1992-12-19	33	175	Kerala	Kochi	2025-06-05	Parents known	\N	Under Investigation
P048	Kartik Joshi	KJ2	1990-07-13	36	180	Maharashtra	Pune	2025-07-27	Sister known	\N	Active
P049	Devendra Rao	DR	1985-10-28	40	183	Telangana	Hyderabad	2025-05-14	Wife known	\N	Active
P050	Amit Solanki	AS2	1993-05-08	33	176	Gujarat	Ahmedabad	2025-08-10	Parents known	\N	Active
\.


--
-- TOC entry 5781 (class 0 OID 24896)
-- Dependencies: 221
-- Data for Name: spatial_ref_sys; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.spatial_ref_sys (srid, auth_name, auth_srid, srtext, proj4text) FROM stdin;
\.


--
-- TOC entry 5966 (class 0 OID 0)
-- Dependencies: 226
-- Name: crime_types_crime_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.crime_types_crime_id_seq', 1, false);


--
-- TOC entry 5967 (class 0 OID 0)
-- Dependencies: 229
-- Name: locations_location_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.locations_location_id_seq', 14, true);


--
-- TOC entry 5794 (class 2606 OID 25695)
-- Name: cases cases_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cases
    ADD CONSTRAINT cases_pkey PRIMARY KEY (case_id);


--
-- TOC entry 5790 (class 2606 OID 25687)
-- Name: crime_types crime_types_crime_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crime_types
    ADD CONSTRAINT crime_types_crime_name_key UNIQUE (crime_name);


--
-- TOC entry 5792 (class 2606 OID 25685)
-- Name: crime_types crime_types_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crime_types
    ADD CONSTRAINT crime_types_pkey PRIMARY KEY (crime_id);


--
-- TOC entry 5796 (class 2606 OID 25717)
-- Name: locations locations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_pkey PRIMARY KEY (location_id);


--
-- TOC entry 5788 (class 2606 OID 25674)
-- Name: persons persons_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.persons
    ADD CONSTRAINT persons_pkey PRIMARY KEY (person_id);


--
-- TOC entry 5797 (class 2606 OID 25701)
-- Name: cases fk_case_crime; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cases
    ADD CONSTRAINT fk_case_crime FOREIGN KEY (crime_id) REFERENCES public.crime_types(crime_id);


--
-- TOC entry 5798 (class 2606 OID 25719)
-- Name: cases fk_case_location; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cases
    ADD CONSTRAINT fk_case_location FOREIGN KEY (location_id) REFERENCES public.locations(location_id);


--
-- TOC entry 5799 (class 2606 OID 25696)
-- Name: cases fk_case_person; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.cases
    ADD CONSTRAINT fk_case_person FOREIGN KEY (person_id) REFERENCES public.persons(person_id);


-- Completed on 2026-09-05 15:27:23

--
-- PostgreSQL database dump complete
--

\unrestrict FdNCXUVUdDbakaX7DJfgiyXNY2uFLkeaA0hpf9hzox0VWXdjXeSxkVuYLb7gUbu

