# Smart Backlog — Requirements & Specification

## Vision

AI-powered personal knowledge hub that captures, categorizes, prioritizes, and plans tasks from multiple input sources. Eliminates browser bookmark chaos by providing intelligent organization with Eisenhower matrix prioritization.

---

## 1. Input Types & Processing

### 1.1 URLs
- Save URL + page title
- Future: parse page content for auto-categorization context

### 1.2 Screenshots
- OCR / Vision AI to extract text and context
- AI interprets content and creates structured note

### 1.3 Voice Messages
- Transcribe audio to text
- Summarize, extract key points
- Reformulate into actionable tasks with proper format

### 1.4 Text / Notes
- Free-form text input
- AI processes and categorizes automatically

---

## 2. Organization

### 2.1 Smart Categorization
- AI creates and suggests categories as items accumulate
- User can create folders and routing rules manually
- When a note enters the backlog, it is processed and placed into the appropriate folder
- Categories evolve over time based on content patterns

### 2.2 Tags
- System tags: `изучить`, `сделать`, `идеи`, `ежедневник`
- User-defined tags (extensible)
- Multiple tags per item

### 2.3 Kanban Boards
- Flexible configuration per task type
- Example: "изучить" + "сделать" on one board, "идеи" on another
- States: To Do → In Progress → Done (customizable)

### 2.4 Daily Planning & Reminders
- Auto-generated daily plan based on priorities and deadlines
- Reminders for selected items
- Future: Google Calendar integration (alarms, push notifications)

---

## 3. Prioritization

### 3.1 Eisenhower Matrix
| | **Urgent** | **Not Urgent** |
|---|---|---|
| **Important** | DO FIRST | SCHEDULE |
| **Not Important** | DELEGATE | ELIMINATE |

- AI suggests quadrant placement based on content analysis
- User can override

### 3.2 Domain Separation
- **Work** (работа)
- **Personal** (личное)
- **Study** (учёба)
- Cross-domain filtering and views

---

## 4. AI Capabilities

### 4.1 Auto-categorization
- Analyze incoming items and assign categories, tags, priority
- Learn from user corrections over time

### 4.2 Priority Suggestion
- Based on content, deadlines, domain, and historical patterns

### 4.3 Summarization
- Condense long articles, voice messages, screenshots into key points

### 4.4 Daily Plan Generation
- Review backlog, priorities, deadlines
- Generate a focused daily plan

### 4.5 Learning Support
- For study-tagged items: generate a learning plan
- Find and attach additional resources/links on request
- Suggest study sequence and dependencies

---

## 5. Interfaces

### 5.1 Telegram Bot
- Quick capture: text, voice, screenshots, links
- Inline commands for viewing boards, daily plan
- Interactive buttons for priority/category selection

### 5.2 MCP Tool
- Full backlog management from VS Code chat
- CRUD operations on items, categories, boards
- Query and filter capabilities

---

## 6. Data & Format

### 6.1 Storage
- SQLite for structured data (items, categories, tags, boards)
- Markdown export for mobile-friendly viewing

### 6.2 Output Format
- Structured Markdown with bullets
- Mobile-friendly (readable on phone)
- Clean hierarchy and formatting

---

## 7. Implementation Phases

### Phase 1 — Foundation
- [ ] Project structure & database schema
- [ ] Core models (Item, Category, Tag, Board)
- [ ] SQLite storage layer
- [ ] Basic LLM integration for categorization

### Phase 2 — Input Processing
- [ ] URL capture (title extraction)
- [ ] Text/note processing pipeline
- [ ] Voice transcription integration
- [ ] Screenshot OCR integration

### Phase 3 — AI Engine
- [ ] Auto-categorization
- [ ] Priority suggestion (Eisenhower matrix)
- [ ] Summarization pipeline
- [ ] Daily plan generation

### Phase 4 — Interfaces
- [ ] Telegram bot (capture + view)
- [ ] MCP tool (full CRUD)

### Phase 5 — Advanced Features
- [ ] Kanban boards with flexible configuration
- [ ] Learning plan generation
- [ ] Google Calendar integration
- [ ] Reminder system
