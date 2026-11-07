---
name: phone-reminder
description: "Plain reminders (\"remind me to X at/in Y\") as zero-LLM cron jobs; the phone app pushes them."
version: 0.1.0
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Reminders, Cron, Mobile]
---

# Phone reminder

Use for plain reminders where the user only wants to be told something at a time
("remind me to drink water in 2 minutes", "every day at 9 remind me to stretch").

Create the job with the cronjob tool, exactly like this:

- `name`: the reminder text, in the user's language, short (e.g. "Su iç").
- `schedule`: the time ("2m", "every 1h", "0 9 * * *").
- `script`: `phone_reminder.sh`
- `no_agent`: true
- `deliver`: `local`

No prompt needed. The job never calls the model, so it costs no quota. The mobile
app watches finished jobs and sends the job name to the phone as a push notification.

Do NOT use this when the job needs thinking at run time (news summary, price check,
"look up X and tell me") — those are normal agent jobs with a prompt, still `deliver: local`.
