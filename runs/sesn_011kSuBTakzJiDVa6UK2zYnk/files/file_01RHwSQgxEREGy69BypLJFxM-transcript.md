# Discovery call transcript: Aisha (Ledgerline)

Q: What are you trying to get an agent to do, and for whom?
A: I want a weekly compliance scan for Ledgerline. It would go through the transactions we've flagged for SME payments and draft the summary we send to the regulator. It's mainly for me and our small compliance team, because compliance is the most boring and most important thing we do. Honestly, I'd love it to write the whole report.

Q: How does that weekly scan and regulator summary get done today, without an agent?
A: Right now one of our analysts pulls the flagged transactions every week, goes through them one by one in a spreadsheet, and writes up a draft summary by hand. Then it comes to me. Nothing goes to the regulator without me reading it. If the agent could send on its own, legal would shut it down on day one. So I review it, fix the wording, and only then does it go out. It takes most of a day for the analyst and a couple of hours for me.

Q: Tell me about the last time you tried to build or run an agent for this. Where did it get stuck?
A: A few months ago I tried to put together a prototype myself to read the flagged transactions and start the draft. Our transaction DB sits inside our VPC. The agent runs in the cloud, so it just couldn't reach it and I gave up. I wasn't comfortable opening the database up to the internet just to test an idea, so it stopped there.

Q: Before you stopped, what did you try in order to get the agent to the data?
A: Honestly, not much. I looked at whether we could expose the database to the agent, but opening anything in our VPC to the outside isn't something I'd do lightly for a test. I did try exporting a small sample by hand to see if the drafting part worked, but a manual export every week defeats the purpose, so I stopped there.

Q: When you ran the drafting on that hand-exported sample, how did the draft turn out?
A: It was better than I expected, honestly. The structure was close to what we send, and it picked out the right transactions to highlight. I still had to tighten the wording in places, which is exactly why I'd always want to read it myself before anything goes out. But it was a small sample, so I never got to see how it would do on a real week.

Q: What has it cost you that the prototype stopped there?
A: Mostly time. The analyst still spends most of a day on it every week, and I spend a couple of hours reviewing, which adds up for a team of twenty-two. It also means one of our more careful people is stuck doing spreadsheet work instead of looking at the genuinely risky cases.

Q: If this worked perfectly next week, what would you see?
A: Oh, I'd love that. On Monday morning I'd open a finished draft of the regulator summary, with the flagged transactions already reviewed and the important ones called out. My analyst would get the day back for real investigative work, and compliance would finally feel a little less boring.

Q: Is there anything I should have asked but didn't?
A: I think you covered the important ground. If anything, I'd want whoever builds this to understand how much trust and control matter to us. We're a compliance company, so anything touching our data or our regulator has to be something I can explain and stand behind. Compliance is the most boring, most important thing we do, and I'd rather it be slow and right than fast and wrong.
