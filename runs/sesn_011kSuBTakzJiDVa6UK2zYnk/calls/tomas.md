# Discovery call transcript: Tomas (Patchwork)

Q: What are you trying to get an agent to do, and for whom?
A: We're Patchwork, a four-person dev-tools team, and I'm building an automated PR reviewer for teams like ours. The idea is a little review squad where each agent owns one concern: one reads the diff, one checks the tests, and one writes the review comment. Eventually I want it to approve trivial PRs by itself, so engineers only look at the ones that actually need a human.

Q: How does PR review get done on your team today, without the agent?
A: Right now it's just us, four engineers, and every PR needs one approval from someone else before it merges. We have CI running the test suite, and then a human reads the diff and leaves comments on GitHub. Honestly a lot of what we review is small stuff like dependency bumps and typo fixes, which is why I want the squad to handle those on its own eventually.

Q: Tell me about the last time you tried to build or run the review squad. Where did it get stuck?
A: Last week I ran it on a mid-sized PR, and it never produced a review. One of the sub-agents just went quiet and the coordinator kept waiting. I had no idea which thread died or why. In the end I killed the whole run and read through the raw logs trying to piece it together, and I never really found out what happened.

Q: When you went through the raw logs, what were you looking for, and what did you actually find there?
A: I was looking for the last thing each sub-agent did before it stopped, basically which one stalled and on what step. What I got was one big interleaved stream with no clean way to tell which agent a line belonged to or what the coordinator thought it was waiting on. I could see the coordinator's last message go out, and after that just nothing, no error and no timeout.

Q: Apart from that run, what else has gotten in the way while building or testing it?
A: Honestly, nothing that stands out, just the usual rough edges you get building something like this. Most of my time has gone into the architecture, getting each agent to own a clean slice of the review and agreeing on what they hand to each other. That part I'm actually pretty happy with.

Q: What did that stalled run, and not knowing what happened, cost you?
A: Mostly an afternoon of digging through logs, and the PR got reviewed by hand anyway. The bigger cost is trust: if I can't tell why a run died, I'm not letting it approve anything by itself. So the whole "auto-approve trivial PRs" goal is on hold until I can actually see what each agent is doing.

Q: If it worked perfectly next week, what would you see?
A: I'd open a PR and a couple of minutes later there's one clean review comment, with the diff concerns and the test gaps pulled together. The dependency bumps and typo fixes would just get approved and merged without any of us touching them. That would be great, honestly. It'd give the four of us back real time every week.

Q: Anything I should have asked but didn't?
A: I think you covered the main stuff, to be honest. Maybe the architecture side, like how the agents split the work and hand off to each other, since that's where most of my thinking has gone. Otherwise I'm good.
