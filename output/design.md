# Dashboard Design: Campus Customs Operations Desk

The dashboard (`frontend/`, React + Vite + TypeScript) is built to feel like a real shop's back-office desk: paper tickets on a board, a team of five people at their desks, a cash register receipt, and checks waiting for a signature. The goal is that someone running the shop can glance at it and know what's open, who's working, what the agents found, and what needs their approval, without reading JSON.

## Layout

Three columns, left to right, follow the way work moves through the shop:

1. **The Board (left).** Every ticket from `/api/tickets` as a paper ticket stub with a big ticket number, its headline, and a status chip (open, working, awaiting approval, blocked, resolved). Click a stub to open it. The rail stays pinned while you scroll.
2. **The Stage (center).** The selected ticket and everything happening on it, top to bottom:
   - **Case file:** the ticket's own fields straight from the database and the **Dispatch the team** button.
   - **Agent floor:** the five agents as five desks.
   - **Live floor:** the activity feed, refreshing every 1.2 seconds while the team works.
   - **Who did what:** appears when the run finishes. The Boss's decision, one card per agent that took part, the drafts left on the board, and next steps.
3. **Money (right).** The **checking balance** at the top and the **approval inbox** below it, both always visible so money is never out of sight.

On narrower screens the money column drops below the board and stage, then everything stacks into one column on a phone.

## Telling agents apart

Each agent has a fixed color, initials avatar, and name, used everywhere it appears:

| Agent | Color | Avatar |
|---|---|---|
| Boss | Yale navy | BO |
| Inventory | Teal | IN |
| Accounting | Green (the same green as the checks) | AC |
| Facilities | Amber | FA |
| Customer Service | Rose | CS |

- On the **agent floor**, agents that joined this ticket light up; the one currently working lifts, glows in its color, and its avatar "breathes." The rest stay faded.
- In the **live feed**, every line has a dot in the agent's color, and the agent's name is printed in that color. Lines are **indented by delegation depth**, so Boss → Accounting → Inventory reads like a conversation tree. Hand-offs get a tinted band and an arrow ("Boss → Inventory: …").
- **MCP tool calls** show as small mono-font chips with a gear and the arguments, separate from what the agent says, so actions and words don't blur together.
- In **Who did what**, each agent's card has a top border in its color.

## Resolved tickets

- When a run ends `resolved`, or ends `awaiting_approval` and a person then approves all of its payments, a green **RESOLVED rubber stamp** thunks onto both the ticket stub and the case file (it drops in big and settles at an angle, like a real stamp).
- The stub's title fades to grey so the open tickets stand out on the board.
- The Boss's verdict block is color-coded by outcome: green for resolved, amber for awaiting approval, red for blocked or needs info.

## Cash balance

- The checking balance (from `/api/cash`, read through MCP from `cash_accounts`) sits on a **receipt**: white paper with a zig-zag torn bottom, a large serif number, and tabular figures so digits don't jump.
- After you approve a payment, the dashboard reloads the balance. The new number ticks in, and a red line shows the last payment (for example **▼ $2,400.00 · rent to Elm City Properties**) with its before → after balances, taken from the payment tool's own result.
- If the payment tool refuses (not enough cash), nothing changes, a toast explains why, and the request moves to history with a red **REFUSED** stamp.

## Approvals

Each pending payment or purchase order is drawn as a **check**: green security-pattern paper, "Pay to" the payee, the amount in large type, then what it's for, which account, why, and the agent's cash check against the balance. **Approve** and **Reject** sit on the bottom right. A red badge counts what's waiting. Decided requests from the current run drop into a short history with PAID, REJECTED, REFUSED, or VOID stamps. Requests from runs wiped by a reset are hidden.

The inbox subtitle says it plainly: *Agents prepare payments. Nothing moves until you approve.*

## Creative touches

- **Perforated ticket stubs.** A CSS mask punches a row of holes down the left edge of each ticket.
- **Rubber stamps** for resolved tickets and approval outcomes, with a "thunk" animation and multiply blending so they look inked onto the paper.
- **Receipt-style cash card** with a torn zig-zag edge.
- **Checks** for approvals, so approving a payment feels like signing one.
- **Dot-grid desk background** in warm paper tones with Yale navy, plus a serif display face (Fraunces) for numbers and headings and a mono face (JetBrains Mono) for tools and data.
- **Typing dots** at the bottom of the feed while agents are thinking, and a red pulsing **LIVE** tag during a run.
- A **pressable Dispatch button** that physically pushes down when clicked.
- A **gpt-6-luna** chip in the header, so it's always clear which model the agents run on.
- **↺ Fresh run** in the header restores the working database (with a confirmation), voids stale approvals, and clears the stage.
- All motion turns off for people who set *reduce motion* in their system settings.

## Why it's built this way

- **Money always visible, never automatic.** Payments are the riskiest action, so the balance and the approval inbox never scroll away, and the only way to pay is a person clicking Approve.
- **Show the work, not just the answer.** The feed shows each delegation, each tool call, and what came back, so a person can check the agents' reasoning against the data before signing anything.
- **Nothing invented on screen.** Ticket fields are shown exactly as the tickets table returns them, and the balance is only displayed if the cash tool actually returned one.
