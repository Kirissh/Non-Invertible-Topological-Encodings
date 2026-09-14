# Your Paper, Explained From A to Z

A complete plain-language walkthrough of **"Privacy as a Property of Representation: Non-Invertible Topological Encodings of Medical Images under Node-Level Differential Privacy."**

This document assumes you know basic probability and linear algebra but nothing about information theory or differential privacy. Every symbol, every theorem, and every technical term in the paper is explained here. Read it top to bottom and you will understand your own submission completely.

---

## Table of Contents

1. [The 60-Second Version](#1-the-60-second-version)
2. [The Problem You Are Solving](#2-the-problem-you-are-solving)
3. [The Big Idea](#3-the-big-idea)
4. [The Pipeline, Stage by Stage](#4-the-pipeline-stage-by-stage)
5. [Math Toolkit: Every Concept Explained](#5-math-toolkit-every-concept-explained)
6. [Every Result in the Paper, Walked Through](#6-every-result-in-the-paper-walked-through)
7. [The Numbers That Matter](#7-the-numbers-that-matter)
8. [Map of the Paper](#8-map-of-the-paper)
9. [Weaknesses and How to Defend Them](#9-weaknesses-and-how-to-defend-them)
10. [Likely Reviewer Questions With Answers](#10-likely-reviewer-questions-with-answers)
11. [Complete Symbol Glossary](#11-complete-symbol-glossary)
12. [What Is Deliberately Not in the Paper](#12-what-is-deliberately-not-in-the-paper)

---

## 1. The 60-Second Version

Hospitals protect medical images by putting a lock on them (encryption) or by scrubbing labels off them (de-identification). Both leave the actual image intact. Break the lock, and you have the patient's biometric data.

Your paper says: stop locking the image and start **changing what the image is**. Convert the slide into a graph, where each cell is a dot (node) and nearby cells are connected by lines (edges). Throw away the pixels entirely. Then add a bit of calibrated random noise to the graph before releasing it.

Now here is the key claim, and it is a claim you actually prove: the graph is **mathematically incapable** of carrying the identity information, because there is not enough room in a graph to store an image. Millions of different slides produce the exact same graph. No key, no attacker, no amount of GPU compute recovers which slide it was, because that information was destroyed before anyone was allowed to ask.

Meanwhile the graph *does* keep the thing doctors need: which cells are near which, what types they are, how they cluster. That is what a pathologist looks at anyway.

Four theorems make this precise. One bounds how much information leaks. One turns that into a floor on how badly any attacker must fail. One bounds how much diagnostic accuracy you lose. One shows this approach needs a privacy budget roughly 100,000 times smaller than adding noise to pixels directly.

---

## 2. The Problem You Are Solving

### 2.1 Two families of existing defense

**Family 1: De-identification.** Strip the metadata, blur the face, crop the edges. The problem is that the *image signal itself* is biometric. Your paper cites two damning results:

- Schwarz et al. (2019) took "defaced" research MRI scans, where the face had been deliberately removed, and recovered patient identities with off-the-shelf face-recognition software.
- Packhäuser et al. (2022) trained a network to re-identify patients from chest X-rays with all header data removed. It worked.

Plus the classic de-anonymization results (Narayanan and Shmatikov 2008, Rocher et al. 2019): sparse high-dimensional records are almost always re-linkable with a bit of side knowledge. A whole-slide image is about as sparse and high-dimensional as data gets.

**Family 2: Cryptography.** Encrypt it, put it in a secure enclave, use federated learning. This is genuinely strong, but the guarantee is *conditional*. It holds as long as:
- nobody loses a key,
- there is no side channel,
- every authorized decryptor behaves,
- the enclave's attestation is not broken.

One failure anywhere and you get the original image back, bit for bit. Homomorphic encryption (Gentry 2009) and federated medical ML (Kaissis et al. 2020) reduce the exposure but do not change *what the data are*.

### 2.2 The unifying observation

Your paper's framing: both families are **access-based**. There is a gate, and behind the gate sits the full sensitive object. Privacy is a statement about who can pass the gate.

The alternative is **representation-based**. Change the object itself so that the sensitive content is not there to be recovered. Then "who has the key" becomes a meaningless question for that content.

This distinction is the paper's central rhetorical move and it is what makes the contribution feel new rather than incremental.

---

## 3. The Big Idea

### 3.1 Two channels in one image

Think of a histopathology slide as carrying two separate kinds of information mixed together:

| Channel | Carries | Example content |
|---|---|---|
| **Texture / intensity** | Identity | exact stain color, illumination, scanner response, sub-pixel nuclear texture, precise cell shape |
| **Topology / arrangement** | Diagnosis | which cells sit next to which, cell-type mix, clustering patterns, tissue architecture |

A pathologist diagnoses from the second channel. A re-identification attack works off the first.

Standard privacy methods protect *both channels equally* by putting a lock over the whole file. Your method **deletes the first channel and keeps the second**. That is the whole thesis in one sentence.

### 3.2 Why deletion is stronger than locking

If you lock something, the information still exists somewhere. If you delete it, no procedure recovers it. The formal version of "delete" here is that the transform is **many-to-one**: enormously many different images map to the exact same graph. Given the graph, you cannot tell which image produced it, not because you lack a key, but because the question has no unique answer.

### 3.3 Why this is not a sacrifice

The nice accident is that computational pathology *already* moved to cell graphs for accuracy reasons, before anyone thought about privacy:

- Pati et al. (2022) built hierarchical cell-to-tissue graphs and they work well.
- Öğüt et al. (2026, GrapHist) pre-trained on 11 million cell graphs and matched vision transformers with **four times fewer parameters**.
- Jaume et al. (2021) showed the topological features these models use are the ones pathologists recognize as diagnostic.

So you are not asking anyone to give up accuracy in exchange for privacy. You are pointing out that a representation the field already likes happens to also be privacy-preserving, and then proving it.

---

## 4. The Pipeline, Stage by Stage

The whole paper studies this chain:

$$I \xrightarrow{\ \Phi\ } G \xrightarrow{\ M\ } \widetilde{G} \xrightarrow{\ \Psi\ } \widetilde{Z}$$

Read it as: image → graph → noisy graph → embedding you publish.

### Stage 0: $I$, the image

$I \in \mathcal{I} \subseteq \mathbb{R}^{H \times W \times C}$.

- $H$ = height in pixels, $W$ = width, $C$ = channels (3 for RGB).
- $m = HWC$ = total number of numbers in the image. For a 1024×1024 RGB slide, $m \approx 3.1$ million.
- $I$ is also treated as a **random variable**: we imagine the image was drawn from some distribution over possible patients. This is what lets us talk about entropy and mutual information.

### Stage 1: $\Phi$, the graph builder

$\Phi = \tau \circ \sigma$. The little circle means "composition": do $\sigma$ first, then $\tau$.

- **$\sigma$ (the segmenter)** finds the cells. Input: image. Output: a set of instance masks, each with a centroid $c_v \in \mathbb{R}^2$ (the cell's x,y position) and a class label. In practice this is a trained CNN like HoVer-Net or StarDist. **Your paper treats $\sigma$ as fixed and public.** This matters enormously and is your #1 stated limitation.
- **$\tau$ (the topology builder)** turns the dots into a graph. Three standard options, all covered by your results:
  - **$k$-nearest-neighbor graph**: connect each cell to its $k$ closest cells.
  - **Delaunay triangulation**: a canonical geometric triangulation of the point set.
  - **Radius graph**: connect $u$ and $v$ if $\|c_u - c_v\|_2 \le r$ for a chosen radius $r$.

The output is $G = (V, E, X_V)$:
- $V$ = the set of nodes (cells). $|V|$ = how many.
- $E$ = the set of edges (adjacency relations).
- $X_V$ = the node attributes.

### Stage 1.5: Assumption 1, the attribute restriction

**This is where your privacy actually comes from, and the paper says so out loud.**

Each node gets an attribute $X_v = \rho(\text{mask}_v)$ drawn from a **finite alphabet** $\mathcal{X}$ with $|\mathcal{X}| = q$ values. Allowed: cell type label, a coarse size class, a bucketed shape descriptor. **Forbidden:** raw pixel intensities, stain response curves, continuous shape descriptors at full precision.

Why this matters: if you let node attributes be high-precision continuous vectors, you could smuggle the entire texture channel back in through the attributes, and every theorem downstream collapses. The paper is explicit that this is an *assumption*, not something proved, and it keeps $q$ visible in every constant so the cost of relaxing it is measurable.

### Stage 1.75: the admissible graph family

$$\mathcal{G}_{n,D,q} = \{(V,E,X_V) : |V| \le n,\ \max_v \deg(v) \le D,\ X_V \in \mathcal{X}^{|V|}\}$$

In words: graphs with at most $n$ nodes, where no node has more than $D$ neighbors, and attributes come from a $q$-letter alphabet. Section 4 of the paper proves the degree bound $D$ is physically justified rather than assumed.

### Stage 2: $M$, the privacy mechanism

$\widetilde{G} = M(G)$. A randomized algorithm satisfying $\varepsilon$-node differential privacy. Concretely this could be adding Laplace noise to graph statistics, randomly flipping edges, or the neighbor-replacement scheme from GraphPrivatizer.

**The paper deliberately does not commit to one mechanism.** Everything holds for *any* $M$ meeting the definition. Constants are instantiated with the Laplace mechanism only where a number is needed.

### Stage 3: $\Psi$, the embedding

$\widetilde{Z} = \Psi(\widetilde{G})$, typically a graph neural network encoder producing a vector in $\mathbb{R}^d$.

**Critical point:** $\Psi$ is *not* a privacy mechanism. Duddu et al. (2020) showed embeddings leak node properties on their own. Your paper handles this by proving (Proposition 2) that $\Psi$ is **post-processing**, so it cannot make things worse or better. Whatever $M$ let through is the ceiling. This is why you don't need to trust the encoder.

### The threat model

The adversary knows $\Phi$, $M$, $\Psi$, and the prior distribution over images. They see $\widetilde{Z}$. They have **unlimited compute**. This is deliberately generous: your guarantee does not depend on keeping the pipeline secret, which distinguishes it from security-through-obscurity schemes.

---

## 5. Math Toolkit: Every Concept Explained

This is the section to read if any symbol in the paper is unfamiliar. Each entry gives the intuition first, then the formal definition.

### 5.1 Information theory

#### Entropy $H(X)$

**Intuition:** how surprised you are, on average, when you learn the value of $X$. Or: how many yes/no questions you need to pin it down.

**Formal:** for a discrete random variable, $H(X) = -\sum_x P(x)\log P(x)$.

**Units:** if $\log$ is base 2, entropy is in **bits**. If natural log, it is in **nats**. 1 nat = 1.4427 bits. Your paper uses nats by default and converts to bits when the numbers read better.

**Example:** a fair coin has $H = 1$ bit. A coin that always lands heads has $H = 0$ (no surprise).

#### Conditional entropy $H(X \mid Y)$

**Intuition:** how much uncertainty about $X$ is *left over* after you already know $Y$.

If $H(I \mid \widetilde{Z})$ is large, the release told you almost nothing about the image. That is exactly what you want.

#### Mutual information $I(X;Y)$

**Intuition:** how much knowing $Y$ reduces your uncertainty about $X$. The overlap between two variables.

**Formal:** $I(X;Y) = H(X) - H(X \mid Y)$.

**Properties you use:**
- $I(X;Y) \ge 0$ always.
- $I(X;Y) = 0$ exactly when $X$ and $Y$ are independent, meaning the release is useless to the attacker.
- $I(X;Y) \le H(X)$ and $I(X;Y) \le H(Y)$.

**In your paper:** $I(I; \widetilde{Z})$ is the master leakage quantity. The whole privacy argument is "make this small."

> ⚠️ **Notation collision to be aware of.** The paper uses $I$ for both the image and mutual information, following the proposal's notation table. So $I(I;\widetilde{Z})$ reads "mutual information between the image $I$ and the release $\widetilde{Z}$." It is standard in both fields, but a reviewer might flag it. Both tables in your paper define it, so you are covered.

#### Differential entropy $h(X)$

The continuous analogue of entropy: $h(X) = -\int p(x)\log p(x)\,dx$.

Unlike discrete entropy it can be **negative**, which is fine and does not break anything. You need it because images live in $\mathbb{R}^m$, a continuous space.

#### Markov chain $U \to X \to Y$

**Intuition:** a relay race. $Y$ only learns about $U$ through $X$. Once you know $X$, knowing $U$ tells you nothing extra about $Y$.

**Why your pipeline is one:** $G = \Phi(I)$ depends only on $I$. $\widetilde{G} = M(G)$ depends only on $G$. $\widetilde{Z} = \Psi(\widetilde{G})$ depends only on $\widetilde{G}$. Each stage sees only the previous stage's output. That is the definition.

#### Data Processing Inequality (DPI)

**Intuition:** *you cannot create information by processing.* Post-processing can only destroy, never manufacture.

**Formal:** if $U \to X \to Y$ is Markov, then $I(U;Y) \le I(U;X)$.

**In your paper:** used constantly. It is why $\Psi$ cannot leak more than $M$ let through, why the attacker's reconstruction cannot beat the release, and why the whole chain collapses to a single bound.

#### Strong Data Processing Inequality (SDPI)

**Intuition:** the DPI says "you don't gain." The SDPI says "you actively *lose*, by a specific factor." If a channel is noisy, information doesn't just fail to increase; it shrinks by a measurable proportion.

**Formal:** $I(U;Y) \le \eta_{\mathrm{KL}}(P_{Y|X})\, I(U;X)$, where $\eta_{\mathrm{KL}} \in [0,1]$ is the **contraction coefficient** of the channel. $\eta = 1$ means no contraction (DPI only). $\eta = 0$ means total destruction.

**References in your paper:** Raginsky (2016), Polyanskiy and Wu (2025).

**This is the engine of Lemma A.** Your differential privacy mechanism is a noisy channel, so it contracts, and you quantify by how much.

#### Total variation distance $\mathrm{TV}(P,Q)$

**Intuition:** the biggest possible disagreement between two probability distributions about the probability of any single event. Ranges from 0 (identical) to 1 (completely distinguishable).

**Formal:** $\mathrm{TV}(P,Q) = \sup_T |P(T) - Q(T)|$.

**Practical meaning:** if $\mathrm{TV} = 0.1$, the best possible test for telling $P$ from $Q$ beats coin-flipping by only 10 percentage points.

#### Dobrushin contraction coefficient $\eta_{\mathrm{TV}}$

The worst-case TV distance between the channel's outputs over all pairs of inputs:

$$\eta_{\mathrm{TV}}(M) = \sup_{g,g'} \mathrm{TV}\big(M(g), M(g')\big)$$

**Key fact you use:** $\eta_{\mathrm{KL}} \le \eta_{\mathrm{TV}}$. The Dobrushin coefficient upper-bounds the KL contraction coefficient, so bounding it is enough. This lets you convert a differential privacy statement (which is naturally about distinguishability) into a mutual information statement.

#### Rate-distortion function $R_X(d)$

**Intuition:** the minimum number of bits you need to describe $X$ if you are willing to tolerate average error $d$. Compression theory, from Shannon.

**Formal:** $R_X(d) = \inf\{I(X;\hat X) : \mathbb{E}[\text{distortion}(X,\hat X)] \le d\}$.

**Properties:** decreasing in $d$ (more error allowed, fewer bits needed) and convex.

**The trick in Theorem 1:** run it backwards. The attacker's reconstruction $\hat I$ has some error $\bar d$. That means $R_I(\bar d) \le I(I;\hat I) \le \eta(\varepsilon)$. Since $R_I$ is decreasing, a small right-hand side forces a *large* $\bar d$. Few bits available means large error is unavoidable.

#### Shannon lower bound

A universal lower bound on the rate-distortion function for squared-error distortion, valid for *any* source with finite differential entropy:

$$R_I(\bar d) \ge h(I) - \tfrac{m}{2}\log(2\pi e\,\bar d)$$

This is what lets Theorem 1 avoid assuming images are Gaussian. You get a bound for real images with unknown distributions.

#### Entropy power

$\frac{1}{2\pi e}e^{2h(I)/m}$. Think of it as "the variance an equivalent Gaussian would need to be as uncertain as $I$ is."

**Why it appears:** as $\varepsilon \to 0$, your distortion floor $\gamma(\varepsilon)$ converges to exactly this. And for a Gaussian source with per-pixel variance $\sigma_I^2$, the entropy power *equals* $\sigma_I^2$. Meaning: the attacker's best strategy degrades to "guess the average image," ignoring the release completely. That is the cleanest possible statement of "the release is useless."

#### Fano's inequality

**Intuition:** if $Y$ carries little information about $X$, then guessing $X$ from $Y$ must fail often. Converts an information bound into an error-probability bound.

**Formal (as used in Corollary 3):** guessing which of $N$ patients produced the release,

$$\mathbb{P}[\hat v \ne v] \ge 1 - \frac{\eta(\varepsilon) + \log 2}{\log N}$$

The $\log 2$ term comes from bounding the binary entropy function $H_b(\cdot) \le \log 2$.

**Why this matters practically:** this is the guarantee a data protection officer actually wants. It speaks about *linkage failure rate*, not about pixel fidelity.

### 5.2 Differential privacy

#### The core definition

A randomized mechanism $M$ satisfies **$\varepsilon$-differential privacy** if for all neighboring inputs $G \sim G'$ and all outcome sets $T$:

$$\mathbb{P}[M(G) \in T] \le e^{\varepsilon}\,\mathbb{P}[M(G') \in T]$$

**Plain English:** the output distribution barely changes whether or not your data was included. An observer cannot confidently tell if you participated.

**Reading $\varepsilon$:**
- $\varepsilon = 0$: perfect privacy, output is independent of the input, zero utility.
- $\varepsilon = 0.1$: very strong.
- $\varepsilon = 1$: strong.
- $\varepsilon = 10$: weak but still formally something.
- $\varepsilon = \infty$: no privacy.

$e^\varepsilon$ is the multiplicative "wiggle room." At $\varepsilon = 0.1$, $e^{0.1} \approx 1.105$, so probabilities can only shift by about 10%.

#### $(\varepsilon,\delta)$-differential privacy

A relaxation: $\mathbb{P}[M(G) \in T] \le e^{\varepsilon}\mathbb{P}[M(G') \in T] + \delta$. The $\delta$ is a small failure probability. Required for the Gaussian mechanism. Your paper sets $\delta = 0$ unless stated.

#### Edge-DP vs node-DP vs graph-DP

This taxonomy is from Mueller et al. (2023), and choosing correctly matters.

| Flavor | What is hidden | Difficulty |
|---|---|---|
| **Edge-DP** | one edge | easy, sensitivity usually $O(1)$ |
| **Node-DP** | one node *and all its edges* | hard, sensitivity can be $O(n)$ or $O(n^2)$ |
| **Graph-DP** | an entire graph | strongest, used for graph classification |

**You chose node-DP**, the harder and stronger option, because in a medical setting the thing to hide is a patient (a node), not a single relationship. Section 4 of your paper is entirely devoted to making node-DP affordable.

#### Neighboring graphs (Definition 1 in your paper)

$G \sim G'$ if $G'$ comes from $G$ by:
- deleting one node $v$ plus all its edges, **or**
- deleting a connected subgraph $S$ with $|S| \le s$ plus all incident edges, **or**
- the corresponding insertion.

The parameter $s$ is the **privacy unit size**:
- $s = 1$: hide one patient. Right choice for a cohort graph where nodes are patients.
- $s > 1$: hide a whole tumor cluster as one unit. Right choice for an intra-slide cell graph, where hiding a single cell is meaningless.

Every sensitivity bound in Section 4 costs a factor of $s$.

#### Global sensitivity $\Delta f$

**Intuition:** how much can one person's data move the answer, in the worst case? This determines how much noise you need.

**Formal:** $\Delta f = \max_{G \sim G'} \|f(G) - f(G')\|_1$.

**The $\ell_1$ norm** $\|x\|_1 = \sum_i |x_i|$: add up the absolute values. (The $\ell_2$ norm $\|x\|_2 = \sqrt{\sum_i x_i^2}$ is the ordinary Euclidean length, used for the Gaussian mechanism.)

#### The Laplace mechanism

Add noise drawn from the Laplace distribution with scale $b = \Delta f / \varepsilon$ to each coordinate of the answer.

**Laplace distribution:** density $\frac{1}{2b}e^{-|w|/b}$. It looks like a two-sided exponential, a sharp peak with fatter tails than a Gaussian.

**Facts your proofs use:**
- $\mathbb{E}|W| = b$ (mean absolute value equals the scale).
- $\mathbb{P}[|W| > bt] = e^{-t}$ (clean exponential tail).
- $\mathrm{Var}(W) = 2b^2$.

**The trade-off in one line:** noise scale $= \Delta f / \varepsilon$. Bigger sensitivity means more noise. Smaller budget means more noise. **This single fraction is why your whole paper works**, because you prove $\Delta f$ is tiny for graphs and huge for pixels.

#### The Gaussian mechanism

Add $\mathcal{N}(0,\sigma^2)$ noise with $\sigma = \Delta_2 f\sqrt{2\log(1.25/\delta)}/\varepsilon$. Gives $(\varepsilon,\delta)$-DP instead of pure $\varepsilon$-DP. Calibrated to $\ell_2$ sensitivity rather than $\ell_1$. Appears as Corollary 4.

#### Post-processing immunity

**Statement:** if $M$ is $\varepsilon$-DP, then $f \circ M$ is $\varepsilon$-DP for *any* $f$, even one chosen adversarially.

**Why:** the definition is about the output *distribution*, and applying a fixed function to both sides of the inequality preserves it.

**Why it is load-bearing for you:** this is Proposition 2(i), and it is what makes the "keyless sharing" argument in Section 5 work. Once you publish $\widetilde{Z}$, anyone can re-embed, retrain, redistribute, or analyze it forever without eroding the guarantee.

#### Composition

**Basic composition:** $k$ releases at budgets $\varepsilon_1,\dots,\varepsilon_k$ give total budget $\sum_j \varepsilon_j$. Privacy loss just adds up.

**Advanced composition (Dwork and Roth 2014):** if you accept a small $\delta'$, you get roughly $\sqrt{2k\log(1/\delta')}\,\varepsilon + k\varepsilon(e^\varepsilon - 1)$, which grows like $\sqrt{k}$ instead of $k$. Much better for many releases.

**Concentrated DP (Bun and Steinke 2016):** tighter still, cited as an option.

**Why this is in the paper:** multi-hospital release. Proposition 2(ii) turns "how many times can we publish?" into arithmetic a governance committee can actually audit.

#### Group privacy

**Statement:** if $M$ is $\varepsilon$-DP for single-record changes, it is $k\varepsilon$-DP for changes involving $k$ records.

**Proof idea:** chain the inequality along a path of $k$ single-step changes, multiplying $e^\varepsilon$ each time.

**Where you use it:** Lemma A, Step 2. You need indistinguishability between *arbitrary* graph pairs, not just neighbors, so you walk along a path of length at most $R$ and pick up $e^{R\varepsilon}$.

#### Neighbor-diameter $R$

Your own term. The maximum number of neighboring-steps needed to get from any admissible graph to any other. Since you can delete every node and then insert every node of the target, $R \le 2\lceil n/s \rceil$.

**Honest consequence:** for intra-slide graphs $n$ is in the thousands, so $R\varepsilon$ is large and the contraction factor $\tanh(R\varepsilon/2) \approx 1$. **Your paper says this out loud** in the Remark after Lemma A rather than hiding it. That honesty is a strength with theory reviewers.

#### Mutual-information DP (Cuff and Yu 2016)

**The result:** $\varepsilon$-DP implies $\sup_v \sup_{P_X} I(X_v; M(X) \mid X_{-v}) \le \varepsilon$ nats.

**Plain English:** differential privacy directly caps how many nats the output reveals about any one person, *given everyone else's data*.

**Why this matters:** it gives you Corollary 1, a bound that does **not** degrade with cohort size $n$. This is the operationally strong version of Lemma A, and you should lead with it when presenting.

### 5.3 Graph theory and linear algebra

#### Degree $\deg(v)$

Number of edges touching node $v$. $D$ denotes the maximum over all nodes.

#### Adjacency matrix $A$

$A_{uv} = 1$ if $\{u,v\} \in E$, else 0. Symmetric, $|V| \times |V|$, zeros on the diagonal.

#### Degree matrix $D_{\deg}$

Diagonal matrix with $\deg(v)$ on the diagonal.

#### Combinatorial Laplacian $L = D_{\deg} - A$

**Intuition:** the graph's version of the second-derivative operator. It measures how much a function on the nodes disagrees with its neighbors.

**Key properties:**
- Symmetric and positive semidefinite, so all eigenvalues are real and $\ge 0$.
- The smallest eigenvalue is always 0.
- The number of zero eigenvalues equals the number of connected components.
- $\mathrm{trace}(L) = \sum_v \deg(v) = 2|E|$. Handy for checking your arithmetic.

#### Normalized Laplacian $\mathcal{L} = D_{\deg}^{-1/2} L D_{\deg}^{-1/2}$

Same idea, rescaled. **Crucial property:** all eigenvalues lie in $[0,2]$ (Chung 1997). This gives you a free sensitivity bound of $2p$ for a top-$p$ summary regardless of degree, which is the content of the Remark after Proposition 6.

#### Spectrum and eigenvalues $\lambda_i$

The eigenvalues of $L$, usually written $\lambda_1 \ge \lambda_2 \ge \cdots \ge \lambda_n$. They encode global structure: connectivity, bottlenecks, cluster count, expansion.

**Worked fact used in your example:** for a Cartesian product graph $P_a \times P_b$, the Laplacian eigenvalues are all pairwise sums of the factors' eigenvalues. The path $P_3$ has eigenvalues $\{0,1,3\}$, so the $3\times3$ grid has $\{0,1,1,2,3,3,4,4,6\}$. (Check: they sum to 24, and $2|E| = 24$. ✓)

**Another:** the cycle $C_n$ has eigenvalues $2 - 2\cos(2\pi k/n)$ for $k = 0,\dots,n-1$.

#### Clustering coefficient

For node $u$, the fraction of $u$'s neighbor pairs that are themselves connected. Measures "how cliquey is my neighborhood." Always in $[0,1]$. The *clustering profile* is the vector of these values over all nodes.

#### Frobenius norm $\|A\|_F$

$\|A\|_F = \sqrt{\sum_{i,j} A_{ij}^2}$. Treat the matrix as one long vector and take its Euclidean length.

#### Hoffman-Wielandt inequality (1953)

**Statement:** for symmetric matrices $A, B$ with eigenvalues sorted in the same order,

$$\sum_i \big(\lambda_i(A) - \lambda_i(B)\big)^2 \le \|A - B\|_F^2$$

**Plain English:** if two symmetric matrices are close entrywise, their eigenvalues are close too. Spectra are stable under small perturbations.

**Why it is the star of Proposition 6:** you would expect removing a node to scramble the whole global spectrum. Hoffman-Wielandt says no: the change is bounded by the Frobenius norm of the difference, and that difference is just a little star subgraph, so it is $O(D)$, not $O(n)$.

#### Star graph and its Laplacian

$\mathrm{Star}_v$ = node $v$ plus its $\deg(v)$ incident edges. Its Laplacian has $\deg(v)$ on the diagonal at $v$, a 1 on the diagonal at each neighbor, and $-1$ in the $2\deg(v)$ off-diagonal slots. So

$$\|L(\mathrm{Star}_v)\|_F^2 = \deg(v)^2 + \deg(v) + 2\deg(v) = \deg(v)^2 + 3\deg(v)$$

#### Cauchy-Schwarz for norms

$\|x\|_1 \le \sqrt{p}\,\|x\|_2$ for $x \in \mathbb{R}^p$. Used to convert the $\ell_2$ spectral bound into the $\ell_1$ bound that the Laplace mechanism needs.

#### Packing argument

A counting technique from discrete geometry: if objects must keep a minimum distance apart and all fit in a bounded region, you can bound how many there are by comparing areas.

Your Proposition 4 uses this. Cells cannot overlap, so a fixed-radius neighborhood can only contain so many of them.

### 5.4 Analysis and asymptotics

#### Lipschitz continuity

A function $u$ is **$L$-Lipschitz** if $|u(x) - u(y)| \le L\|x - y\|$.

**Plain English:** the output cannot change faster than $L$ times the input change. No cliff edges.

**Why you need it:** to say "a little noise causes a little utility loss," you must rule out a classifier whose decision flips wildly for tiny perturbations. $L$ is the conversion rate from noise to accuracy loss.

**Honest note:** $L$ is the constant most likely to be large in practice for a deep network, and your Limitations section says so.

#### $\tanh$ and the inequality $\tanh(x) \le x$

$\tanh(x) = \frac{e^x - e^{-x}}{e^x + e^{-x}}$, an S-curve from $-1$ to $1$ with $\tanh(0) = 0$.

The identity $\frac{e^x - 1}{e^x + 1} = \tanh(x/2)$ is what turns the raw DP total variation bound into the clean $\tanh$ form. And $\tanh(x) \le x$ for $x \ge 0$ gives you the linearization $\eta(\varepsilon) \le \tfrac{1}{2}R\varepsilon\,\mathcal{C}$, which is what makes "$\eta \to 0$ as $\varepsilon \to 0$" obvious.

#### $\Theta(\cdot)$

$\Theta(m)$ means "grows exactly proportionally to $m$," up to constants. Used in Proposition 3 to say the budget-threshold ratio scales linearly with the pixel count.

#### Jensen's inequality

For a concave function $\varphi$, $\mathbb{E}[\varphi(X)] \le \varphi(\mathbb{E}[X])$. Used in the fiber-cardinality proof to turn a conditional entropy into a statement about the average fiber size.

#### The binomial sum bound

$\sum_{j \le k}\binom{N}{j} \le \left(\frac{eN}{k}\right)^k$. A standard counting bound, used to count degree-bounded graphs in Proposition 1.

---

## 6. Every Result in the Paper, Walked Through

### Proposition 1: Fiber cardinality and residual uncertainty

**What it says:**
$$\log|\mathcal{G}_{n,D,q}| \le \underbrace{\frac{nD}{2}\log\frac{en}{D} + n\log q}_{\mathcal{C}(n,D,q)}$$
and therefore $H(I \mid G) \ge H(I) - \mathcal{C}(n,D,q)$.

**Plain English:** there are only so many possible graphs. A graph is a small object. So a graph simply cannot store an image, and after seeing the graph you still have almost all of your original uncertainty about the image.

**"Fiber"** means the preimage $\Phi^{-1}(G)$: the set of all images that produce this particular graph. The proposition says the average fiber is astronomically large.

**How the proof works:**
1. A graph with max degree $D$ has at most $nD/2$ edges (each edge has 2 endpoints, each node contributes at most $D$).
2. Count edge-subsets of that size from $\binom{n}{2}$ possible edges, using the binomial bound.
3. Multiply by $q^n$ for the attribute choices.
4. Take logs.
5. Since $\Phi$ is deterministic, $H(G \mid I) = 0$, so $I(I;G) = H(G)$, so $H(I\mid G) = H(I) - H(G)$.

**Why this is the most important result in the paper even though it is only a proposition:** $\mathcal{C}(n,D,q)$ contains **no $H$, no $W$, no $C$**. It does not depend on image resolution *at all*. Buy a better scanner, quadruple the image entropy, and the ceiling does not move a millimetre. That is your paradigm shift, expressed as an inequality.

**The numbers:** with $n = 5000$ nuclei, $D = 35$, $q = 8$: $\mathcal{C} \approx 7.7 \times 10^5$ bits. A 1024×1024 RGB 8-bit image: $2.5\times 10^7$ bits. Ratio about 33×. The typical fiber holds on the order of $2^{2.4\times 10^7}$ different images that all give the identical graph.

### Proposition 2: Closure under post-processing and composition

Three parts:

**(i) Post-processing.** $\Psi \circ M$ is $\varepsilon$-node-DP for any $\Psi$, even adversarially chosen. This is why the embedding is a convenience, not a defense, and why downstream reuse is free.

**(ii) Composition.** $k$ sites releasing at $\varepsilon_j$ each give $\sum_j \varepsilon_j$ total, or the better advanced-composition bound $\varepsilon' = \sqrt{2k\log(1/\delta')}\varepsilon + k\varepsilon(e^\varepsilon-1)$.

**(iii) Transfer to the image domain.** The guarantee stated over graphs implies the corresponding guarantee over images whose graphs are neighbors.

**Why it is in the paper:** it is the technical backbone of the "keyless, no per-query overhead" e-health argument in Section 5.

### Lemma A: Vanishing mutual information

**What it says:**
$$I(I;\widetilde{Z}) \le \eta(\varepsilon) := \tanh\!\left(\frac{R\varepsilon}{2}\right)\mathcal{C}(n,D,q)$$

**Plain English:** the total leakage is (how much a graph can possibly hold) × (how much the noise shrinks it). Both factors are working for you, and the second goes to zero as $\varepsilon$ does.

**The four proof steps, unpacked:**

1. **Markov + DPI.** The chain $I \to G \to \widetilde{G} \to \widetilde{Z}$ is Markov, so $I(I;\widetilde{Z}) \le I(I;\widetilde{G})$. The embedding is free; ignore it.

2. **Group privacy + a small optimization.** Walk from any graph to any other in $\le R$ neighbor-steps, picking up $e^{R\varepsilon}$. Then solve a two-variable constrained optimization to get the sharpest TV bound. Set $a = P(T)$, $b = Q(T)$; the constraints $b \ge ae^{-R\varepsilon}$ and $1-b \le e^{R\varepsilon}(1-a)$ are both tight at the optimum, giving $a = 1/(1+e^{-R\varepsilon})$ and
$$\mathrm{TV} \le \frac{e^{R\varepsilon}-1}{e^{R\varepsilon}+1} = \tanh(R\varepsilon/2)$$
That maximized quantity is the Dobrushin coefficient.

3. **SDPI.** Since $\eta_{\mathrm{KL}} \le \eta_{\mathrm{TV}}$, we get $I(I;\widetilde{G}) \le \tanh(R\varepsilon/2)\cdot I(I;G)$.

4. **Plug in Proposition 1.** $I(I;G) = H(G) \le \mathcal{C}(n,D,q)$. Multiply and you are done.

**The honest caveat (stated in the paper's Remark):** in the **intra-slide regime**, where $G$ is one image's cell graph, $R$ scales with the number of nuclei, so $\tanh(R\varepsilon/2) \approx 1$ at any realistic budget. The bound then degenerates to the structural ceiling alone. The paper says this plainly instead of burying it. That is why Proposition 1 is stated separately: in that regime, $\Phi$ carries the argument and $M$ is a refinement.

### Corollary 1: Per-patient conditional bound

**What it says:** in a **cohort graph** (nodes are patients),
$$I(I_v; \widetilde{Z} \mid G_{-v}) \le \varepsilon \ \text{nats}$$
uniformly in $n$, $H$, $W$, and $C$.

**Plain English:** even if the attacker already knows every other patient's data, the release tells them at most $\varepsilon$ nats about patient $v$'s image. Independent of cohort size and independent of scanner resolution.

**Why it is arguably stronger than Lemma A:** no $R$, no $n$, no degradation. It comes straight from Cuff and Yu's equivalence between $\varepsilon$-DP and $\varepsilon$-MI-DP, plus two applications of conditional DPI.

**Concrete meaning:** $\varepsilon = 0.1$ nats $= 0.144$ bits. The image itself carries tens of megabits. You are leaking a fraction of one bit.

**Presentation advice:** when you give the talk, lead with this corollary. It is the crispest number in the paper.

### Theorem 1: Lower bound on adversarial reconstruction error

**What it says:** for **every** measurable, possibly randomized attacker $\mathcal{A}$,

$$\mathbb{E}\left[\tfrac{1}{m}\|I - \mathcal{A}(\widetilde{Z})\|_2^2\right] \ge \gamma(\varepsilon) := \frac{1}{2\pi e}\exp\left(\frac{2}{m}\big(h(I) - \eta(\varepsilon)\big)\right)$$

**Plain English:** no attacker, ever, using any method, can reconstruct the image better than this error floor. It is not "we tried some attacks and they failed." It is "no attack can succeed."

**Proof in three moves:**
1. $I \to \widetilde{Z} \to \hat I$ is Markov, so DPI gives $I(I;\hat I) \le \eta(\varepsilon)$.
2. By definition of the rate-distortion function, the pair $(I,\hat I)$ is feasible, so $R_I(\bar d) \le \eta(\varepsilon)$.
3. Shannon lower bound: $R_I(\bar d) \ge h(I) - \tfrac{m}{2}\log(2\pi e\bar d)$. Combine and solve for $\bar d$.

**The beautiful limit:** as $\varepsilon \to 0$, $\gamma(\varepsilon) \to \frac{1}{2\pi e}e^{2h(I)/m}$, the entropy power. For a Gaussian source of per-pixel variance $\sigma_I^2$ this equals **exactly $\sigma_I^2$**, which is the error you get from the trivial estimator that ignores $\widetilde{Z}$ and outputs the mean image. Interpretation: the attacker is provably reduced to guessing the population average. The release contributed nothing.

**Corollary 2 (bounded adversaries):** any class $\mathcal{B}$ (polynomial-time algorithms, GraphMI-style gradient inversion, anything) is a *subset* of all measurable maps, so the bound applies unchanged. This is the sentence that answers the GraphMI literature: optimization does not create information, so no amount of attack engineering breaches $\gamma(\varepsilon)$. The bound is indifferent to compute budget, architecture, and gradient access.

**Corollary 3 (Fano re-identification):** $\mathbb{P}[\text{wrong patient}] \ge 1 - \frac{\eta(\varepsilon)+\log 2}{\log N}$. With $N = 10^4$ and $\eta = 0.1$ nats: at least **0.91**. The attacker gets it wrong at least 91% of the time.

**Remark (auxiliary information):** if the attacker holds side information $S$, replace $h(I) \to h(I\mid S)$ and $\eta \to I(I;\widetilde{Z}\mid S)$. In the cohort regime Corollary 1 already gives the conditional form. The paper explicitly declines to claim a guarantee against an attacker who already has a near-copy of the slide, noting that no scheme, including encryption, can offer that. **Reviewers respect this kind of scoping.**

### Theorem 2: Upper bound on diagnostic utility loss

**Setup:** $f: \mathcal{G} \to \mathbb{R}^p$ is the topological summary the diagnostic model consumes (say, degree histogram + top Laplacian eigenvalues + clustering profile). $u: \mathbb{R}^p \to \mathbb{R}$ is the task head. $U^* = u(f(G))$ is the clean utility.

**What it says:** with the Laplace mechanism and $L$-Lipschitz $u$,
$$U^* - \mathbb{E}[u(\tilde f)] \le \kappa\frac{\Delta f}{\varepsilon}, \qquad \kappa = Lp$$
and with probability $\ge 1-\beta$,
$$U^* - u(\tilde f) \le Lp\frac{\Delta f}{\varepsilon}\log\frac{p}{\beta}$$

**Plain English:** how much accuracy you lose = (task sensitivity) × (query sensitivity) ÷ (privacy budget). Three knobs, all interpretable.

**The proof is genuinely short:**
- Lipschitz gives $|u(f) - u(\tilde f)| \le L\|W\|_1$.
- Laplace with scale $b$ has $\mathbb{E}|W_j| = b$, so $\mathbb{E}\|W\|_1 = pb = p\Delta f/\varepsilon$.
- Multiply.
- For the high-probability version: union bound over $p$ coordinates with the tail $\mathbb{P}[|W_j| > bt] = e^{-t}$ at $t = \log(p/\beta)$, then $\|W\|_1 \le p\|W\|_\infty$.

**Corollary 4** gives the Gaussian-mechanism analogue for $(\varepsilon,\delta)$-DP.

**Why the form matters:** this is exactly the $\kappa\Delta f/\varepsilon$ shape your proposal called for, and it isolates the two quantities GraphPrivatizer identifies as governing structural perturbation. Section 4 then proves $\Delta f$ is small.

### Proposition 3: Pareto dominance at matched budget

**The fair comparison.** Both routes protect the same unit, run at the same $\varepsilon$, feed the same head $u$ through the same summary $f$. Only the injection point differs:

- **Graph route:** $\tilde f_g = f(\Phi(I)) + \mathrm{Lap}(\Delta_g/\varepsilon)^{\otimes p}$, with $\Delta_g \le c_f s D$.
- **Pixel route:** $\tilde I = I + \mathrm{Lap}(\Delta_{px}/\varepsilon)^{\otimes m}$, then compute $f(\Phi(\tilde I))$, with $\Delta_{px} = mB$.

**Certified utility floor:** $\underline{U}(\varepsilon) = \max\{U^* - \kappa\Delta/\varepsilon,\ U_0\}$, where $U_0$ is chance level. This is the best each route's *own guarantee* can promise.

**Usable budget threshold $\varepsilon_{\min}$:** the smallest budget at which the floor beats chance.

**The three claims:**

(i) $\underline{U}_{\text{graph}}(\varepsilon) \ge \underline{U}_{\text{pixel}}(\varepsilon)$ for every $\varepsilon$, once $m \ge \kappa_g c_f s D/(\kappa_p B)$.

(ii) $$\varepsilon_{\min}^{\text{graph}} = \frac{\kappa_g c_f s D}{U^* - U_0}, \qquad \varepsilon_{\min}^{\text{pixel}} = \frac{\kappa_p m B}{U^* - U_0}, \qquad \text{ratio} = \Theta(m)$$

(iii) On the whole interval $[\varepsilon_{\min}^{\text{graph}}, \varepsilon_{\min}^{\text{pixel}})$ the graph route certifies useful accuracy and the pixel route certifies nothing. That interval widens linearly in the pixel count.

**The one-sentence intuition:** graph sensitivity is capped by *maximum node degree*. Pixel sensitivity grows with *number of pixels*. Degree is a biological constant. Pixels are whatever your scanner does. So the graph route's noise requirement is fixed while the pixel route's explodes with resolution.

> **Scoping you should memorize before the Q&A.** The paper's Remark states plainly that this compares *certified floors*, not realized accuracies, and is a *sufficient condition*, not an impossibility result. A pixel-space mechanism that privatizes a low-dimensional image summary would avoid the factor $m$; but such a mechanism is philosophically closer to yours than to naive pixel noise. The separation is proved against mechanisms constrained to stay in the pixel domain, which is exactly the constraint that motivates access-based approaches. Upgrading to a true impossibility result is listed as open work.

### Proposition 4: Packing bound on cell-graph degree

**What it says:** if nuclei centroids are at least $r_{\min}$ apart and $\tau$ builds the radius-$r$ graph,
$$\deg(v) \le \left(1 + \frac{2r}{r_{\min}}\right)^2 - 1$$
For the symmetrized $k$-NN graph, $\deg(v) \le 7k$ in the plane.

**Plain English:** cells are physical objects with physical size. Only so many can fit within radius $r$ of another cell. That is a fact about tissue, not a mathematical convenience.

**The proof is a picture:** put a disk of radius $r_{\min}/2$ on each neighbor. Separation makes them disjoint. They all sit inside the disk of radius $r + r_{\min}/2$ around $v$. Compare areas:
$$k\pi(r_{\min}/2)^2 \le \pi(r + r_{\min}/2)^2 \implies k \le (2r/r_{\min} + 1)^2$$

The $k$-NN clause uses the classical fact that a planar point is the nearest neighbor of at most six others (Eppstein, Paterson, Yao 1997), so at most $6k$ points have it among their $k$ nearest; add its own out-degree $k$ to get $7k$.

**Why this is the most reviewer-pleasing move in Section 4:** node-DP normally requires assuming a degree bound out of thin air, which reviewers hate. You *derive* it from a measurable property of the tissue preparation. $r_{\min}$ is the minimum nuclear separation, which a pathologist can measure. $r$ is your own choice.

**Numbers:** $r = 15\,\mu m$, $r_{\min} = 6\,\mu m$ gives $D \le (1+5)^2 - 1 = 35$. A symmetrized 5-NN graph gives the same 35. Compare to the $n \approx 5000$ that unrestricted node-DP would force. That is a 140× reduction in required noise.

### Proposition 5: Sensitivity of combinatorial queries

For removal of at most $s$ nodes from a degree-$\le D$ graph:

| Query | Bound | Reason |
|---|---|---|
| edge count | $sD$ | every destroyed edge touches a removed node |
| degree histogram | $s(2D+1)$ | $s$ nodes vanish from their bins, plus $\le sD$ neighbors each shift bins (2 units of $\ell_1$ each) |
| triangle count | $s\binom{D}{2}$ | triangles through $v$ are indexed by neighbor pairs |
| clustering profile | $s(D+1)$ | only $S \cup N(S)$ changes, each coordinate lives in $[0,1]$ |
| attribute histogram | $s$ | one bin drops by one per removed node |

**Every bound is free of $n$ and free of resolution.** That is the point.

**The degree-histogram bound is tight**, and the worked example exhibits a graph attaining it exactly.

### Proposition 6: Sensitivity of Laplacian spectra

**What it says:**
$$\left(\sum_{i=1}^n \big(\lambda_i(L) - \lambda_i(\hat L')\big)^2\right)^{1/2} \le s\sqrt{D^2 + 3D}$$
and hence the top-$p$ spectral summary has $\ell_1$ sensitivity $\le s\sqrt{p}\sqrt{D^2+3D} \le s\sqrt{p}(D+2)$.

**Why it is surprising:** eigenvalues are *global*. Intuitively, deleting a node should scramble everything. It does not.

**The trick.** Pad $L(G\setminus v)$ with a zero row and column so both matrices are $n\times n$. Then the difference $L - \hat L'$ is *exactly* the Laplacian of the little star at $v$. That star has Frobenius norm squared $\deg(v)^2 + 3\deg(v) \le D^2 + 3D$. Hoffman-Wielandt converts that entrywise closeness into eigenvalue closeness. Done.

For $s > 1$, remove nodes one at a time and apply the triangle inequality, which costs a factor $s$. (Your roadmap notes this telescoping is loose and an induction accounting for the shared boundary should improve it toward $\sqrt{s}$.)

**Free alternative:** the normalized Laplacian has all eigenvalues in $[0,2]$, so the top-$p$ summary has sensitivity $\le 2p$ regardless of $D$. Useful when the degree bound is loose; costs you the scale information.

### Enforcing the degree bound

Radius and $k$-NN graphs satisfy the bound automatically. Delaunay triangulations can have high-degree vertices in adversarial configurations, and segmentation artifacts create spurious dense clusters.

**Fix:** a projection $\Pi_D$ that greedily deletes edges until every degree is $\le D$, then release $f \circ \Pi_D$.

Two facts make it work:
1. $\Pi_D$ is the identity on graphs already satisfying the bound, so no utility is lost in the normal case.
2. Kasiviswanathan et al. (2013) show the composed query's sensitivity is within a small constant of the degree-bounded-family sensitivity.

The paper also lists smooth sensitivity (Nissim et al. 2007), restricted sensitivity (Blocki et al. 2013), and Day et al.'s (2016) specialized degree-distribution estimator as drop-in improvements rather than rivals.

### The worked example (verify it yourself)

$G$ = the $3\times3$ grid graph. 9 nodes, 12 edges, $D = 4$. Degrees: four corners at 2, four edge-midpoints at 3, one center at 4. Remove the center (worst case), $s=1$.

**Edge count.** Loses 4 edges. Bound $sD = 4$. **Exactly tight.**

**Degree histogram.** Before: $(0,0,4,4,1)$ over bins 0–4. After removing the center, the remainder is the 8-cycle $C_8$, all degree 2: $(0,0,8,0,0)$. The $\ell_1$ distance is $4+4+1 = 9$. Bound $s(2D+1) = 9$. **Exactly tight.**

**Spectrum.** Grid eigenvalues (pairwise sums of $P_3$'s $\{0,1,3\}$): $\{0,1,1,2,3,3,4,4,6\}$. $C_8$ eigenvalues padded with a zero: $\{0,0,2\pm\sqrt2 \text{ pairs},2,2,4\}$. The $\ell_2$ distance between ordered spectra is $\sqrt{9.86} \approx 3.14$, inside the bound $\sqrt{28} \approx 5.29$. The $\ell_1$ distance is $8.0$ against the ceiling $\sqrt{9}\sqrt{28} \approx 15.87$.

**Pixel comparison.** Diagnostic head consumes the 5-dim degree histogram, $L$-Lipschitz, $\varepsilon = 1$. Theorem 2 certifies loss $\le \kappa\Delta f/\varepsilon = 5L \times 9 = 45L$. The pixel route at the same budget calibrates to $\Delta_{px} = 512\times512\times3 = 786{,}432$. Ratio $\approx 8.7\times10^4$, roughly five orders of magnitude.

---

## 7. The Numbers That Matter

Memorize these five for your talk and your defense.

| Quantity | Value | What it proves |
|---|---|---|
| Structural ceiling $\mathcal{C}$ | $7.7\times10^5$ bits vs $2.5\times10^7$ bits for the image | A graph is ~33× too small to hold a slide, and the gap is resolution-independent |
| Typical fiber size | $\sim 2^{2.4\times10^7}$ images per graph | Astronomically many slides give the identical graph |
| Per-patient leakage | $\le \varepsilon = 0.1$ nats $= 0.144$ bits | Independent of cohort size and resolution |
| Re-identification failure | $\ge 91\%$ with $N = 10^4$, $\eta = 0.1$ | Linkage attacks fail 9 times out of 10 |
| Sensitivity ratio | $786{,}432 / 9 \approx 8.7\times10^4$ | Graph route needs ~5 orders of magnitude less noise |

Supporting constants: $D \le 35$ from the packing bound at $r=15\mu m$, $r_{\min}=6\mu m$; equivalently $7k$ with $k=5$.

---

## 8. Map of the Paper

| Section | Content | Key objects |
|---|---|---|
| **1. Introduction and the Paradigm Shift** | access-based vs representation-based privacy; the two-channel argument; positioning against three literatures; three contributions | Eq. (1), the pipeline |
| **2. Mathematical Formulation and System Pipeline** | notation tables; $\Phi = \tau\circ\sigma$; Assumption 1; admissible family; the many-to-one collapse; neighboring graphs; threat model | Tables 1–2, Figure 1, Assumption 1, Definitions 1–2, Propositions 1–2 |
| **3. Core Theoretical Results** | the four headline claims with proof sketches | Lemma A, Corollary 1, Theorem 1, Corollaries 2–3, Theorem 2, Corollary 4, Proposition 3 |
| **4. Graph Sensitivity and Node-Level Bounds** | why node-DP is affordable here; geometry-derived degree bound; explicit sensitivities; projection; hand-checkable example | Propositions 4–6, worked example |
| **5. Significance, Limitations, and Roadmap** | e-health impact; six honest limitations; five planned extensions; closing | narrative |
| **Appendix A** | complete proofs of all propositions, the lemma, both theorems, and the corollaries | full arguments |

The paper is 33 pages in APA manuscript format (double-spaced, `man` class option). Switching line 4 to `jou` gives a two-column journal layout and roughly halves the page count.

---

## 9. Weaknesses and How to Defend Them

The paper states six limitations. Here is each one plus the defense, so you are never caught off guard.

**1. Fixed segmentation.** $\sigma$ is treated as fixed, public, deterministic. Adaptive attacks on segmentation, poisoning, or a segmenter trained on the same patients are entirely outside the model.
> *Defense:* this is stated first because it is the biggest gap, and it is scoped as future work with a concrete plan (Roadmap item 4: certified robustness radius for $\sigma$, propagated through $\tau$). Reviewers punish hidden gaps, not acknowledged ones.

**2. The attribute restriction is an assumption.** Assumption 1 is where privacy originates and it is not proved.
> *Defense:* you prove *consequences* of it and keep $q$ visible in every constant so the cost of relaxing it is measurable. Proving a quantizer is non-identifying needs either an empirical study (out of scope for theory) or a formal model of "biometric," which does not exist yet.

**3. The intra-slide mutual information bound is weak.** When $R$ scales with nuclei count, $\tanh(R\varepsilon/2)\approx 1$ and Lemma A collapses to the structural ceiling.
> *Defense:* say it before they do. The strong statement is Corollary 1 in the cohort regime. And the structural ceiling alone is still a real result, which is why Proposition 1 stands separately.

**4. Certified floors are not realized accuracies.** Proposition 3 compares guarantees, not measured performance.
> *Defense:* stated in a Remark, and upgrading it is Roadmap item 3 with a specific technical route (minimax lower bound via packing plus Assouad or Fano).

**5. No empirical validation.** Every constant is derived, never measured. $L$ is the shakiest.
> *Defense:* this is a purely theoretical track by design, matching the proposal. Point at GrapHist and Pati et al. for the empirical evidence that the graph representation is diagnostically sufficient.

**6. Repeated release and drift.** Budget consumption over time is handled; re-imaging and re-graphing with a different $\tau$ is not.

---

## 10. Likely Reviewer Questions With Answers

**"Isn't this just applying node-DP to a graph? What's new?"**
Node-DP on social graphs assumes the graph is the data. Here the graph is the *output of a lossy transform applied to something more sensitive*, and that changes the analysis: you get a structural ceiling (Proposition 1) that has no analogue in the social-graph setting, and the privacy question becomes about the upstream image, not the graph. Nobody has combined the three literatures this way.

**"Why should I believe the degree bound?"**
Because it is derived, not assumed. Proposition 4 gets it from a packing argument on physical nuclear separation. And for constructions where it can fail (Delaunay), the projection $\Pi_D$ restores it at bounded cost.

**"GraphMI recovers adjacency. Doesn't that break you?"**
No, and Corollary 2 says why. GraphMI is a member of the class of all measurable reconstruction operators, and Theorem 1 lower-bounds error over that entire class. Gradient optimization does not create information.

**"What if the attacker has auxiliary information?"**
Handled in the Remark after Corollary 3: swap $h(I) \to h(I\mid S)$. In the cohort regime Corollary 1 is already conditional on all other patients. The paper explicitly declines to defend against an attacker holding a near-copy of the slide, noting that encryption cannot either.

**"Your Pareto claim seems too strong."**
It is deliberately scoped. It compares certified floors and is a sufficient condition, and the paper says so in a Remark. The stronger impossibility statement is listed as open.

**"$\varepsilon$-DP with $\varepsilon = 0.1$ on graph statistics: is the utility actually usable?"**
Theorem 2 gives the bound; whether it is usable depends on the Lipschitz constant $L$, which the paper flags as the quantity most likely to be large in practice. This is honest scope, and it is why the roadmap includes mechanism design tailored to cell-graph geometry.

**"Why is there no experiment?"**
By design. This is the theoretical track described in the proposal. The claims are lemmas and theorems, not measurements.

---

## 11. Complete Symbol Glossary

### Pipeline objects

| Symbol | Read as | Meaning |
|---|---|---|
| $I$ | "eye" | the image, in $\mathbb{R}^{H\times W\times C}$; also a random variable |
| $\mathcal{I}$ | script I | the image space |
| $m = HWC$ | | number of scalar entries in the image |
| $\Phi$ | Phi | the graph generation transform, $\Phi = \tau\circ\sigma$ |
| $\sigma$ | sigma | the segmenter (image → instance masks) |
| $\tau$ | tau | the topology builder (masks → graph) |
| $G = (V,E,X_V)$ | | the graph: nodes, edges, attributes |
| $\mathcal{G}_{n,D,q}$ | | admissible graph family |
| $c_v$ | | centroid of cell $v$ in $\mathbb{R}^2$ |
| $A$ | | adjacency matrix |
| $D_{\deg}$ | | degree matrix |
| $L$ | | combinatorial Laplacian $D_{\deg} - A$ |
| $\mathcal{L}$ | script L | normalized Laplacian |
| $X_V$ | | node attribute matrix |
| $\mathcal{X}$, $q$ | | attribute alphabet and its size |
| $\rho$ | rho | the attribute quantizer |
| $\Psi$ | Psi | the embedding map (GNN encoder) |
| $Z$, $\widetilde{Z}$ | Z, Z-tilde | clean and released embeddings |
| $\widetilde{G}$ | G-tilde | the privatized graph $M(G)$ |
| $M$ | | the privacy mechanism |
| $\mathcal{R}$ | | the full release map $\Psi\circ M$ |

### Privacy and information

| Symbol | Read as | Meaning |
|---|---|---|
| $\varepsilon$ | epsilon | privacy budget (smaller = more private) |
| $\delta$ | delta | failure probability in $(\varepsilon,\delta)$-DP |
| $\Delta f$ | Delta f | global node sensitivity, $\ell_1$ |
| $\Delta_2 f$ | | global node sensitivity, $\ell_2$ |
| $\Delta_g$, $\Delta_{px}$ | | graph-route and pixel-route sensitivities |
| $G \sim G'$ | "G neighbors G-prime" | the neighboring relation, Definition 1 |
| $s$ | | privacy unit size (nodes per unit) |
| $R$ | | neighbor-diameter of the graph family |
| $H(\cdot)$, $H(\cdot\mid\cdot)$ | | entropy, conditional entropy |
| $h(\cdot)$ | | differential entropy |
| $I(\cdot\,;\cdot)$ | | mutual information |
| $\mathcal{C}(n,D,q)$ | | structural information ceiling |
| $\eta(\varepsilon)$ | eta | leakage bound from Lemma A |
| $\eta_{\mathrm{TV}}$, $\eta_{\mathrm{KL}}$ | | Dobrushin and KL contraction coefficients |
| $\gamma(\varepsilon)$ | gamma | distortion floor from Theorem 1 |
| $\mathrm{TV}(P,Q)$ | | total variation distance |
| $R_I(d)$ | | rate-distortion function |
| $\mathrm{Lap}(b)$ | | Laplace distribution with scale $b$ |
| $W$ | | the noise vector |

### Task and adversary

| Symbol | Meaning |
|---|---|
| $\mathcal{A}$ | a reconstruction operator (the attacker) |
| $\mathcal{B}$ | a class of admissible adversaries |
| $\hat I$ | the attacker's reconstruction $\mathcal{A}(\widetilde{Z})$ |
| $f$ | the topological summary query, $\mathbb{R}^p$-valued |
| $u$ | the diagnostic task head |
| $U(\cdot)$, $U^*$, $U_0$ | utility, clean utility, chance-level utility |
| $\underline{U}(\varepsilon)$ | certified utility floor |
| $\varepsilon_{\min}$ | usable budget threshold |
| $L$, $L_2$ | Lipschitz constants |
| $\kappa = Lp$ | the combined task constant |
| $p$ | dimension of the summary |
| $n$, $D$, $B$ | node bound, degree bound, pixel dynamic range |
| $\Pi_D$ | the degree-truncation projection |

---

## 12. What Is Deliberately Not in the Paper

Knowing the negative space is as important as knowing the content, because it tells you what *not* to claim in the talk.

- **No experiments.** No datasets, no accuracy numbers, no attack implementations. Purely theoretical by design.
- **No commitment to a specific mechanism.** Everything holds for any $\varepsilon$-node-DP $M$. Laplace appears only where a constant was needed.
- **No commitment to a specific $\Psi$.** It is treated as an arbitrary measurable map, which is stronger than fixing a GNN architecture.
- **No claim of unconditional privacy.** Privacy is conditional on Assumption 1, and the paper says so in the Core Thesis subsection, not buried in limitations.
- **No claim against segmentation attacks.** Explicitly excluded.
- **No claim that pixel-space DP is impossible.** Only that it cannot certify as much at matched budget.
- **No claim to replace encryption.** The paper says explicitly that it does not replace encryption in transit or at rest, and does not remove the need for governance. It changes the *failure mode*.

---

## Appendix: Rebuilding the PDF

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Four passes are needed: the first resolves structure, `bibtex` builds the reference list from `references.bib`, and the last two settle cross-references and citation labels.

**Layout options** (line 4 of `main.tex`):
- `man`: APA manuscript, double-spaced, one column. Current setting.
- `jou`: two-column journal layout, roughly half the page count.
- `doc`: single-spaced, single column.

**Before submitting**, replace the placeholders on the title page: `\author{}`, `\affiliation{}`, and the `\authornote{}` contact block.
