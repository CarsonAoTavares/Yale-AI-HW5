# AI Prompt Log

This file records the prompts I typed to my coding assistant (Claude Code) for Homework 5: Campus Customs Multi-Agent Operations. It has one section per problem.

---

## Setup: Workspace and assignment background

### Prompt entered

> yo im wokring in Homework 5 folder today put my stuff there

### Prompt entered

> here is the background "
>
> Homework 5: Campus Customs Multi-Agent Operations
>
> Scenario
>
> Build a team of AI agents to manage the daily operations of Campus Customs. The shop uses a board to track outstanding tasks, including customer orders, rent, unpaid invoices, discount requests, and other operational needs.
>
> The system will have three connected components: an MCP server, a FastAPI backend that runs the agent team, and a React dashboard where a person can monitor activity and approve requests.
>
> All agents must be able to communicate with and delegate tasks to one another. Create the following agents:
>
> - Boss: Reviews tickets, assigns work to the appropriate agents, and makes final decisions.
> - Inventory: Checks availability by SKU and size, identifies shortages, and determines which vendors can replenish stock.
> - Accounting: Monitors cash and invoices, evaluates margins, and prepares payments or purchase orders for human approval.
> - Facilities: Manages matters related to the shop's premises, including leases and rent.
> - Customer Service: Prepares draft messages for customers.
>
> Data
>
> Download and extract `data.zip` to obtain `data/campus_customs.db`, the shop's original database. It contains these tables: `desk`, `tickets`, `inventory`, `pricing`, `vendors`, `leases`, `cash_accounts`, `payments`, `invoices`
>
> The tools will modify database records as tickets are resolved. Create a working copy named `data/campus_customs_new.db` and configure both the MCP server and backend to use it. Preserve the original `campus_customs.db` so you can restore the starting data whenever necessary.
>
> Shop Rules
>
> - Treat `desk.date_today` as the shop's current date when determining whether something is overdue.
> - Retrieve vendor lead times from the `vendors` table.
> - Vendors will not dispatch additional merchandise while an unpaid invoice remains open.
> - Every payment requires human approval. Skipping approval will result in a grading deduction. After completing a payment, update the corresponding database table.
> - The payment tool must reject transactions when available cash is insufficient. Account balances cannot become negative.
> - This assignment models cash outflows only. Revenue and incoming cash are excluded.
> - Restore the working database to its original values before each complete run through the tickets.
> - Do not email customers or contact actual vendors. Keep all communication drafts on the board.
>
> AI Configuration
>
> Use `PORTKEY_API_KEY` to make AI requests. Every agent must use only `gpt-6-luna` through Portkey. Multi-agent conversations can consume tokens quickly, so monitor usage. Any other model appearing in the code or execution will result in a grading deduction.
>
> Workflow and Submission
>
> Complete one problem at a time with your coding assistant, describing each task in your own words. Do not provide the assignment's page URL or screenshots as a shortcut for completing all the problems.
>
> Submit the completed project as a public GitHub repository. The final problem provides the required file structure.
>
> " - also, seems i swiched to claude code, the luna one may not apply -just use whatever the replacement

Outcome: the assistant pointed out that the `gpt-6-luna` requirement applies to the agents in the app, not to the coding assistant, so all agents will use `gpt-6-luna` through Portkey.

### Prompt entered

> so create AI_Prompts.md at the assignemnt and make sure everything has been updated in this file as it's the log of what i typed. put one section fo reeach problem. each section must include: 1. the problem number and title, at least onne prompt you typed,

### Follow-up prompt

> 3. include also one follow-up pompt if i need

What the first prompt was missing: it was cut off before saying that each section should also have a follow-up prompt when one was needed.

---

## Problem 1: Explore the database and start the harness

### Prompt entered

> open data/campus_customs.db and look through every table and its fields. Copy the orignal file to data/campus_customs_new.db - later problems update that working copy. Study the three open tickets so you see how they link to other tables. start output/harness.md. for each table, list the fileds and one short line on what that table matters for the agents. you will keep growing this harness file later

---

## Problem 2: Write the MCP server with the first three tools

### Prompt entered

> write an mCP server in the mcp_server/ using FastMCP. It will talk to data/campus_customs_new.db. you do not need to connect or run it in this problem. Every agent in this homeowork uses the tools in this MCP SERVER. You will add more tools ot it later; for now, write three tools you know you will need tfor the tickets int he database. keep th enames clear. never invent any data, only use informaiton in the database

### Follow-up prompt

> in output/harness.md, list each of your three MCP tools. for every tool include which table it reads, which tickeet it helpsunlock (101,102, 103) and one sentence on why that tool is the right one for that ticket. Vauge lines like reads inveotory, score low, -tie the tool to the ticket. Also, add a short mcp_server/README.md file that explains what the MCP server is for, which database file it uses, and the three tools it has

What the first prompt was missing: it didn't say to document each tool in the harness, tied to the specific ticket it unlocks, or to add a README for the MCP server.

---

## Problem 3: Connect the MCP server to the coding assistant

### Prompt entered

> add the MCP server to this project so the vibe coder can call the tools. Save the connection JSON text in .mcp.json at the project root (or however, you vibe coder saves local mcp server lists)

---

## Problem 4: Smoke-test the three MCP tools

### Prompt entered

> test each of the three MCP tools. Save the evidence in output/mcp_smoke.json . fo rever tool, inludes: the prompt you asked the vibe coder, the tool name, the tool output (must match values in data/campus_customs_new.db

---

## Problem 5: Build the agent team and grow the MCP tools

### Prompt entered

> next: problem 5 - buidl the agent team and grow the MCP tools. buidl the agentic team for cmapus cusotms using PydanticAI: Boss, inventory, accounting, facilities, and customer service. Inlcude prompts, models, and agent loops so they can delegate work to each other with full connectviity.

### Prompt entered

> Store each agent's prompt in a separate file within `backend/prompts/`. Define data types in `backend/models.py` and place the agent implementation files under `backend/`. You may organize the files differently, provided the five agent roles remain clearly identifiable. Use `PORTKEY_API_KEY` and exclusively `gpt-6-luna` for all agents.
>
> Write each prompt in your own words and include the shop rules relevant to that agent. Detailed prompts that fully explain the agent's responsibilities and scope will receive higher scores than brief, generic prompts.

### Prompt entered

> Add any tools the gents need to your MCP server so they can work on the open tickets. Shop facts come from the MCP server over data/campus_customs_new.db - do NOT invento a second shop-tools laywer that bypasses MCP.

### Follow-up prompt

> Configure the agents to append execution records to `output/audit_trail.json`. Each step of the agent loop should capture enough information for later auditing. Preserve existing entries and add new records rather than clearing the file between runs.
>
> In `output/harness.md`, document every agent and MCP tool, including any tools introduced in this problem, and identify the database tables each tool uses. Include a brief safety section describing safeguards for interactions involving real customers and money, along with limits to control token consumption.
>
> Update `mcp_server/README.md` to reflect the current set of tools.

What the first prompts were missing: they didn't ask for an audit trail of each agent step, or for the harness and MCP README to document every agent, tool, safeguard, and token limit.

---

## Problem 6: Plan the three tickets

### Prompt entered

> problme 6: plan the three tickets - before you wire the backend, write down what you expect the team to do on each open tiecket. Build output/desk_tickets.html - a page you can double-click with one tab per ticket (101, 102, 103). also add empty cash and reflection tabs for later problems (leave them or with a short coming later note for now). on each ticket tab, fill an expected section only. (leave room for an Actual section you will fill after you run the agents)

### Follow-up prompt

> for each tickets, expected section, writ e it in your own words:
>
> Identify which agent the Boss should contact first and explain why.
>
> - Describe every expected delegation between agents, rather than simply stating that the Boss contacts everyone.
> - Specify which MCP tools you expect the run to use.
>
> Plans that involve every specialist in every ticket will receive lower scores. After the agents resolve the three tickets, compare their actual actions with your original plan.

What the first prompt was missing: it didn't say what each Expected section must contain (first agent contacted and why, each delegation, which MCP tools), or that plans shouldn't use every specialist on every ticket.

---

## Problem 7: Backend routes

### Prompt entered

> Problem 8: backend routes: your reaction frontend dashboard (the nextd problem) needs a backend it can call. in backend/main.py   use FastAPI and add routes that do the follwing
>
> Return all three tickets and indicate whether each is open or resolved.
>
> - Accept a ticket ID and run the agent team on that ticket.
> - Provide recent agent activity, including messages and tool usage, so the board can refresh.
> - Process a payment or purchase only after a person clicks Approve. Agents prepare the payment request; this route executes it and updates cash.
> - Retrieve the current checking account balance from `cash_accounts`.
> - Restore the database to its original values to start a fresh run.

### Prompt entered

> from the backend/ folder, start the server with uvicorn main:app --reload --port 8000

### Follow-up prompt

> this turns on your backend at the http://localhost;8000 so the frontend dashboard can call those routes. In output/harness.md, list each route in one line (what URL/What it does)

What the first prompts were missing: they didn't ask for the routes to be documented in the harness, one line each.

---

## Problem 8: Agent dashboard

### Prompt entered

> problem 8: Agent Dashboard; buidld the frontend dashboard in frontend/ with React +Vite + TypeScript. the page shoudl callt he routes you built in problem 7. At minimum, the board shoudl:
>
> Display all three tickets.
>
> - Allow the user to select one ticket and launch the agent team to work on it.
> - Show each agent's messages and actions as the ticket is being processed.
> - Mark the ticket as resolved when the run finishes.
> - Provide a brief summary of each agent's contribution to that ticket.
> - Allow a person to approve payment or purchase requests.
> - Display the checking account balance and update it to reflect the decrease after an approved payment.
>
> Create an attractive, thoughtfully designed dashboard. Use a creative layout and visual style to make it a workspace people would enjoy using.

### Prompt entered

> tell the front end to talk to your backend at http://localhost:8000, on the backend, allow the vite page orgina (usually http://localhost:5173) so the browder is allowed to call those routes. npm run dev

### Follow-up prompt

> This opens the React dashboard in your browser, allowing you to select tickets and monitor the agents as they work.
>
> Create `output/design.md` to explain your dashboard's design and the reasons behind it. Describe the layout, how users can distinguish between agents, and how resolved tickets and cash balances are displayed. Include the creative touches that make the dashboard distinctive and enjoyable to use.
>
> make srue the earlier steps you ahd "
>
> Return all three tickets and indicate whether each is open or resolved.
>
> - Accept a ticket ID and run the agent team on that ticket.
> - Provide recent agent activity, including messages and tool usage, so the board can refresh.
> - Process a payment or purchase only after a person clicks Approve. Agents prepare the payment request; this route executes it and updates cash.
> - Retrieve the current checking account balance from `cash_accounts`.
> - Restore the database to its original values to start a fresh run.
>
> "

What the first prompts were missing: they didn't ask for a written explanation of the design (`output/design.md`), or say to double-check that the dashboard covers every Problem 7 route.

---

## Problem 9: Resolve the tickets

### Prompt entered

> problem 9: resolve the tickets: Before testing the agents across all three tickets, restore `data/campus_customs_new.db` to its original state and record the initial checking account balance. Then run tickets 101, 102, and 103 from the board all being resolved. Open `output/desk_tickets.html`, created in Problem 6. For each ticket tab, complete the **Actual** section with details from this run: which agents participated, what tasks they delegated, and which tools they used. Preserve the **Expected** section so you can compare the planned workflow with what actually happened.

### Follow-up prompt

> on the cash tab of the same output/desk_tickets.html, itemize the money:
>
> Starting checking balance (after the reset)
>
> - For each ticket: how cash changed when that ticket resolved, and why (which pay / purchase, dollar amount)
> - Ending checking balance — it must match `cash_accounts` in the working database
>
> Wrong cash math loses points even if the board shows every ticket resolved. Also save:
>
> - `output/resolved_tickets.json` — for each ticket: id, final status, short outcome, what each agent contributed, and any human approvals
> - `output/resolved_board.html` — a page you can double-click with a screenshot of your React board for each resolved ticket (101, 102, and 103)
>
> Append real runs to `output/audit_trail.json`. Finish `output/harness.md` so it covers tables, MCP tools, the five agents, API routes, the dashboard, and safety rules.

What the first prompt was missing: it didn't ask for the cash breakdown on the Cash tab, the resolved-tickets JSON, the board screenshots page, or for the audit trail and harness to be finished.

---

## Problem 10: Reflection

### Prompt entered

> open output/desk_tickets.html and fill the Reflection tab. anser in your own vibe, and be detaield and thorough:
>
> Assess how well the agents performed on each ticket and explain your reasoning.
> Compare the actual results for each ticket with the expected plan you developed earlier.
> Identify which tasks would have been easier for a single agent equipped with tools, and explain why.
> Describe three new challenges Campus Customs could encounter that this agent team could address using the tools you built.
> Describe three new challenges Campus Customs could encounter that the team could not address with its existing tools. Explain which additional tools and agents would be needed to resolve them.

### Follow-up prompt

> tie every answer to this app and the three tikets you ran- use the ticket tabs and cash tab on the same page as your evidence. generic AI essays without Campus Customs details will score low

What the first prompt was missing: it didn't say every answer had to cite this app's three ticket runs and cash results, using the ticket and Cash tabs as evidence.

---

## Problem 11: Submit the project on GitHub

### Prompt entered

> Push your code to a public GitHub repository so graders can clone it. Submit the repo URL to Canvas, and also put it in output/github_url.txt. Do not push your real .env to the GitHub repo. Do include both database files under data/ (the original and your working copy) so graders can run your app easily. expected layout "
>
> ```
> hw5/
> ├── AI_prompts.md
> ├── requirements.txt
> ├── .env.example
> ├── .gitignore
> ├── .mcp.json
> ├── README.md
> ├── data/
> │   ├── campus_customs.db
> │   └── campus_customs_new.db
> ├── mcp_server/
> │   ├── server.py
> │   └── README.md
> ├── frontend/
> ├── backend/
> │   ├── main.py
> │   ├── models.py
> │   └── prompts/
> │       ├── boss.md
> │       ├── inventory.md
> │       ├── accounting.md
> │       ├── facilities.md
> │       └── customer_service.md
> └── output/
>     ├── harness.md
>     ├── mcp_smoke.json
>     ├── desk_tickets.html
>     ├── design.md
>     ├── resolved_tickets.json
>     ├── resolved_board.html
>     ├── audit_trail.json
>     └── github_url.txt
> ```
>
> " README should explain: copy original DB to the working copy when you need a clean run, start MCP server, start FastAPI backend, start the React board, reset the DB before a full three-ticket run.

### Follow-up prompt

> why are these missing? can you make it not missing "
>
> What was kept out: I checked that your real `.env` isn't in the repo; only `.env.example` with a placeholder key is. `.venv` and `node_modules` aren't pushed either. Neither are the Homework 3 photos in `data/`; the repo is set to accept only the two database files there.
> Still missing from the expected layout:
>
> - data/campus_customs.db and data/campus_customs_new.db
> - mcp_server/server.py and mcp_server/README.md
> - output/mcp_smoke.json, `resolved_tickets.json`, `resolved_board.html`, and `audit_trail.json` with real runs
>
> Also, `.mcp.json` points at mcp_server/server.py, which doesn't exist yet, so it won't connect until the server is written.
> Once the Homework 5 `data.zip` is in `Homework 5/`, I'll finish Problems 1–4, 6, 9 and 10, add both databases and push again. The URL stays the same, so you can submit it to Canvas then.

### Follow-up prompt

> i jsut dropped the data-2 folder - and complete all the missing steps or stuff

### Follow-up prompt

> i got into the data -3 folder - try it again, fix everything and update github

What the first prompt was missing: the Homework 5 database itself. `data-2` turned out to be the older store database, and `data-3/campus_customs.db` had the nine Homework 5 tables, which unblocked every remaining problem.

### Follow-up prompt

> so all done? giv eme the new link and everthing i need to submit fo rmy homework

### Follow-up prompt

> can you show me my website

### Follow-up prompt

> ok tell me when its all pushed

### Follow-up prompt

> for the failed one - what should i do?

What the earlier prompts were missing: they didn't cover what happens when an agent run fails partway. The answer was to retry temporary Portkey errors automatically, reset the database, and rerun all three tickets from a clean start.

---

<!-- One section per problem goes below, e.g.
## Problem N: <Title>

### Prompt entered

> <exact prompt typed>

### Follow-up prompt (only if needed)

> <exact follow-up typed>

What the first prompt was missing: <one sentence>
-->
