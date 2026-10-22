# Mathematical Conventions and Correctness Scope

The underlying space is T^d=R^d/Z^d, with d=1 or 2. R_g is an invertible integer matrix, s_g is a group character taking values ±1, and q_g is a rational shift. Use column vectors and fix

\[
F_g(k)=s_gR_gk+s_gq_g,\qquad F_{gh}=F_g\circ F_h.
\]

Affine composition is (A,b)(C,c)=(AC,b+Ac), and the inverse is (A⁻¹,−A⁻¹b). Under k'=k+theta, all shifts vanish if and only if the same theta satisfies

\[
(R_g-s_gI)\theta=q_g\pmod{\mathbb Z^d}.
\]

Supported inputs use canonical presentations of C2, C4, or C2xC2, at most two generators, matrix entries with absolute value ≤2, and normalized q denominators ≤8. The linear representation need not be faithful. General group finiteness and complete multiplication-table inputs are not implemented.

Check the schema, R and s relations, and complete affine relations before stacking B and q. An integer left-null vector w with wB=0 and nonintegral wq is an impossibility certificate. Failure to find such a candidate does not establish solvability.

The implementation uses the exact fallback in plan Section 5.2: restrict theta to [0,1]^d, enumerate the finite integer residuals z using row extrema, and enumerate vertices of each rational cube slice. A nonempty compact polytope has a vertex. Fixing d-r independent coordinate boundaries produces a full-rank system at a suitable vertex, so complete enumeration is exhaustive. Budget exhaustion remains unresolved.

The independent certificate check uses the following complete-grid bound. If Q is a common denominator of q, r is the rank of B, and L is the least common multiple of the absolute values of all nonzero r-by-r minors, a feasible vertex has a denominator dividing QL. This grid can therefore check existence. Merely using the input q denominator would not be complete. The checker caps the grid at 250,000 points and does not claim verification when the cap is exceeded.

A Smith normal form backend with U/V transformations, a parameterization of the full solution set, and complete H¹ classification are not implemented. Rank is diagnostic information. All inputs describe abstract affine toy actions; no physical SSG or material realization has been verified.

## Conditional experimental kernels (v0.3 preview)

`verifier/orientation.py` adds rational Cartesian director and collinear unpolarized-neutron calculations, separate from the torus convention above. It checks D=n n^T/|n|² under supplied single-domain orthogonal operations and P(n,Q)=1-(n·Q)²/(|n|²|Q|²). Independent checks use Rn=±n and the cross-product norm respectively. See the [discovery specification](design/discovery_benchmark_rsi.md) for nuisance scales, domain mixtures, finite identifiability and physical limitations. These kernels do not establish magnetic group assignment, propagation vectors, allowed reflections, energy stability or experimental signal size.
