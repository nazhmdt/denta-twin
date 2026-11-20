# DentaTwin - Digital Twin and Virtual Clinic for a Dental Clinic

Final course project, **Digital Twins and Metaverse** (AI in Business), group AIB-2401.
Team: Zhumadilova Nazerke, Nurlan Inzhu, Bagdar Zhansaya. Professor: Gulnara Abitova.

DentaTwin is a prototype Digital Twin of the treatment area of a fictional three-chair dental clinic.
A 3D web scene shows the status of every chair hour by hour, a transparent rule scores each booking's
no-show risk, and a virtual clinic lets patients see free slots from the twin and confirm their visit.

**All data in this repository are synthetic.** The prototype is not connected to any real clinic system.

## Live links
- 3D twin and virtual clinic: https://denta-twin.onrender.com
- Dashboard (Looker Studio): https://datastudio.google.com/reporting/efa831bf-625f-4053-83c0-681895c87e35
- Video walkthrough: https://youtu.be/v83EE3j8ANM

## Repository structure
| Path | What it is |
| --- | --- |
| `index.html` | The whole 3D twin and virtual clinic in one page (three.js, data embedded as JSON) |
| `src/gen_data.py` | Python script that generates the synthetic week, computes KPIs and evaluates the risk rule |
| `data/dental_clinic_appointments_synthetic.csv` | Generated dataset: 144 chair-hours, 23 fields |
| `data/summary.json` | KPIs, results by chair, confusion matrix, threshold comparison, benefit estimate |

## How to run
1. Data and evaluation: `pip install pandas` then `python src/gen_data.py` (fixed random seed 42, so the output is reproducible).
2. 3D twin: open `index.html` in a browser with internet access (three.js and fonts load from public CDNs), or open the Render link above.
3. Deployment: the repository is served on Render as a free Static Site (no build command, publish directory `.`).

## Logic in short
- **Unit of the twin:** one chair-hour (3 chairs x 8 hourly slots x 6 days = 144 records).
- **KPIs:** chair utilization = attended chair-hours / available chair-hours; no-show rate = no-shows / bookings;
  revenue per chair-hour = revenue of attended visits / available chair-hours.
- **Risk rule:** score = new patient (+1) + booked more than 7 days ahead (+1) + reminder not confirmed (+1);
  High risk if score >= 2. In Google Sheets:
  `=IF(I2="Booked", (J2="New")+(K2>7)+(L2="No"), "")`
- **Chair colour in the twin:** green = attended, red = no-show, grey = free slot, orange ring = high-risk booking.
- **Recommendation in the virtual clinic:** earliest free slot for the chosen service (shorter lead time lowers risk).

## Looker Studio calculated fields
| Field | Formula |
| --- | --- |
| Chair Utilization | `SUM(Attended_Flag)/SUM(Chair_Hours)` |
| No-show Rate | `SUM(NoShow_Flag)/SUM(Booked_Flag)` |
| Revenue per Chair-hour | `SUM(Revenue_KZT)/SUM(Chair_Hours)` |

## Results on the synthetic week
Utilization 61.1%, no-show rate 17.8%, revenue per chair-hour 11,500 KZT.
The rule flags 46 of 107 bookings and catches 13 of 19 no-shows (recall 68.4%, precision 28.3%).

## Use of AI tools
Claude (Anthropic) helped write the data-generation script and the 3D scene code. The team defined the problem,
scope, KPIs and rule, reviewed all code and checked every number against the dataset.
