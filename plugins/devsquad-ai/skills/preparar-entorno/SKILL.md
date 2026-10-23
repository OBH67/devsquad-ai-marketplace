---
description: Verifies that the necessary tools (Node.js, npm, git) are installed before writing the first line of code of a DevSquad AI project, and guides the person to install them — including the notice to ask IT for permission if they are on a work computer with restrictions. Always use before the coder starts implementing; never assume they are already installed.
---

# Prepare the local environment

Do not assume the person already has the necessary tools installed. This
already caused real friction in a DevSquad AI project: it was assumed from
the start that the Node tools to run `npm` already existed, and it was never
verified nor warned about in advance.

## Steps

1. **Check what is installed**, using Bash:

```
node -v
npm -v
git --version
```

Adjust the list to what the stack chosen in `.devsquad/arquitectura.md`
requires (for example, if Python was chosen instead of Node, check
`python3 --version` instead).

2. **If everything is installed and in a reasonable version**, say so briefly
and continue — there is no need to dwell on this any longer.

3. **If something is missing**, explain in simple language what it is and why
it is needed (e.g. "Node is the program that makes it possible to run your
app's code on your computer — without it I can't show you how it looks").
Give them the concrete step to install it (the official site, not an
improvised tutorial):
- Node.js + npm → nodejs.org (download the LTS version)
- git → git-scm.com

4. **Explicitly warn about restricted work computers**, always, without
waiting for an installation to fail:

> "If you're using a computer from your work, you may not have permission to
> install new programs. Before trying to install this, ask your IT team
> (Information Technology) whether they can install it for you or authorize
> you to do it. That way we avoid you running into a 'permission denied'
> error halfway through."

5. **Do not continue to write code until the person confirms that the tools
are ready.** If they cannot install something because of their company's
restrictions, report it to the Orchestrator — the project may need to pause
there until IT authorizes it, and the person must know that this is the
reason, not a system error.

## With someone non-technical

Do not ask them to "run commands" without first explaining, in one sentence,
what is going to happen and why it is safe to do it.
