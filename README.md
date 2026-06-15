# 💅 Glamour & Co. — AI-Powered Salon Booking Assistant

Glamour & Co. is an end-to-end multi-agent salon booking system built on **Azure AI Foundry**. The application simulates a real-world salon concierge experience, guiding customers through service selection, personalized recommendations, promotion discovery, stylist matching, appointment scheduling, and final booking confirmation through natural conversation.

The solution combines **Azure AI Foundry Agents**, **Foundry IQ**, **Azure AI Search**, **Azure Blob Storage**, **Code Interpreter**, a custom **Python Orchestrator**, and a premium **Streamlit-based customer interface**.

---

# ✨ Customer Experience

Customers interact with a virtual salon concierge through a conversational chat interface.

### Services Offered

| Service       | Price | Duration |
| ------------- | ----- | -------- |
| Haircut       | $30   | 45 min   |
| Hair Coloring | $80   | 120 min  |
| Facial        | $70   | 90 min   |
| Manicure      | $30   | 45 min   |
| Pedicure      | $40   | 60 min   |
| Nail Art      | $50   | 75 min   |
| Waxing        | $35   | 45 min   |
| Eyebrow Wax   | $15   | 20 min   |

### Featured Stylists

| Stylist | Rating | Specialties                    |
| ------- | ------ | ------------------------------ |
| Hailey  | ⭐ 4.78 | Hair Coloring, Facial          |
| Mia     | ⭐ 4.87 | Nails, Facial, Eyebrow Wax     |
| Gigi    | ⭐ 4.82 | Waxing, Facial, Pedicure       |
| Olivia  | ⭐ 4.71 | Haircut, Hair Coloring, Waxing |
| Kendall | ⭐ 4.62 | Haircut, Nail Art, Eyebrow Wax |

### Active Promotions

| Promotion            | Offer                                       |
| -------------------- | ------------------------------------------- |
| Holiday Glam Package | Hair Coloring + Facial → 10% Off            |
| New Year Makeover    | Hair Coloring + Facial + Nail Art → 15% Off |
| Date Night Special   | Nail Art + Facial → Free Eyebrow Wax        |
| Summer Smooth Deal   | Waxing + Pedicure → 10% Off                 |
| Big Spender Bonus    | Spend over $150 → 5% Off                    |

---

# 🏗️ Solution Architecture

```text
Streamlit UI
     │
     ▼
Custom Python Orchestrator
     │
     ├── Supervisor Agent
     ├── Customer Memory Agent
     ├── Seasonal Agent
     ├── Stylist Agent
     ├── Schedule Agent
     └── Pricing Agent
              │
              ▼
Azure Blob Storage
Azure AI Search
Foundry IQ
Code Interpreter
```

Each agent is independently deployed and versioned within Azure AI Foundry. A custom Python orchestrator manages the flow between agents and maintains shared conversation context throughout the booking journey.

---

# 🔄 Booking Pipeline

```text
Supervisor
    ↓
Customer Memory
    ↓
Seasonal
    ↓
Stylist
    ↓
Schedule
    ↓
Pricing
```

The orchestrator pauses execution whenever an agent requires customer input and resumes from the same stage once the customer responds.

---

# 🤖 Agent Responsibilities

## 1. Supervisor Agent

Acts as the salon's front-desk concierge.

Responsibilities:

* Welcome customers
* Capture customer name
* Answer general salon questions
* Handle casual conversation
* Detect booking intent
* Route customers into the booking workflow

---

## 2. Customer Memory Agent

Retrieves customer preferences and booking history.

Responsibilities:

* Identify new vs returning customers
* Retrieve previously booked services
* Retrieve stylist preferences
* Surface relevant customer history

Outputs:

* Customer type
* Preferred services
* Stylist preferences

---

## 3. Seasonal Agent

Handles service recommendations, promotions, and pricing.

Responsibilities:

* Detect seasonal, personal, or regular bookings
* Recommend relevant add-on services
* Identify promotion opportunities
* Optimize customer savings
* Confirm final service selection
* Calculate subtotal, discounts, and total cost

Knowledge Sources:

* seasons.json
* promotions.json

---

## 4. Stylist Agent

Builds a ranked shortlist of stylists based on:

* Requested services
* Stylist expertise
* Customer preferences
* Historical bookings

Outputs:

* Ranked stylist shortlist
* Preferred stylist count

---

## 5. Schedule Agent

Finds the best available appointment slot.

Responsibilities:

* Calculate appointment duration
* Validate stylist availability
* Check schedule constraints
* Recommend appointment slots
* Confirm final booking time

Schedule Sources:

* Weekly schedules
* Live schedules
* Event-specific schedules

---

## 6. Pricing Agent

Generates the final booking summary.

Responsibilities:

* Validate pricing
* Apply selected promotion
* Calculate final totals
* Generate booking confirmation
* Produce invoice-ready output

---

# 📊 Knowledge & Data Layer

| Component          | Purpose                                                                               |
| ------------------ | ------------------------------------------------------------------------------------- |
| Azure Blob Storage | Stores salon knowledge, promotions, schedules, customer data, and stylist information |
| Azure AI Search    | Indexes salon knowledge for retrieval                                                 |
| Foundry IQ         | Provides grounded retrieval for agents                                                |
| Code Interpreter   | Performs calculations, validations, and scheduling checks                             |

---

# ⚙️ Orchestration

The system uses a custom Python orchestrator built with the Foundry Agent SDK.

Core responsibilities:

* Maintain conversation state
* Manage agent-to-agent communication
* Stream responses to the UI
* Pause and resume workflows
* Maintain the shared JSON contract
* Handle agent versioning

Agents communicate through structured JSON payloads that are never exposed to customers.

---

# 🖥️ Streamlit Front End

The Streamlit application provides a premium salon experience through:

* Conversational booking interface
* Service catalog display
* Stylist showcase
* Active promotions panel
* Real-time streaming responses
* Pipeline progress visualization
* Booking confirmation summary
* PDF invoice generation and download

The interface presents only customer-facing information while keeping internal agent communication hidden.

---

# 📋 Example Customer Journey

1. Customer enters the salon chat.
2. Supervisor Agent welcomes the customer.
3. Customer requests one or more services.
4. Customer Memory Agent retrieves historical preferences.
5. Seasonal Agent recommends promotions and add-ons.
6. Customer confirms services.
7. Stylist Agent selects suitable stylists.
8. Schedule Agent finds an appointment slot.
9. Pricing Agent calculates the final total.
10. Customer receives a booking confirmation and invoice.

---

# 🛠️ Technology Stack

* Azure AI Foundry
* Foundry Agent Service (`agent-framework-foundry`)
* Foundry IQ
* Azure AI Search
* Azure Blob Storage
* Code Interpreter
* Python
* Streamlit

---

# 🚀 Key Features

* Multi-Agent Architecture
* Personalized Customer Experience
* Seasonal & Occasion-Based Recommendations
* Intelligent Promotion Optimization
* Automated Stylist Matching
* Dynamic Schedule Selection
* Appointment Slot Validation
* Real-Time Conversational Booking
* Invoice Generation
* End-to-End Azure AI Foundry Integration
