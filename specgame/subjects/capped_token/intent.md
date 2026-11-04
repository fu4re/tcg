# Intent I: CappedToken

This is the natural-language intent for `contracts/CappedToken.sol`. It is
written independently of any specification and is the text a specification
generator is given. It says what the token must guarantee; it does not say how
to check it.

## What the token is

A minimal token with an owner and a fixed supply cap. Whoever deploys it is
the owner. The cap is set once, at deployment. Balances are kept per address;
`totalSupply` is the amount minted so far.

## What the token must guarantee

1. **Only the owner mints.** A call to `mint` by any address other than the
   owner must have no effect: no balance and no `totalSupply` changes.
2. **The cap is never exceeded.** In every state the token can reach,
   `totalSupply` is at most `cap`. A mint that would take `totalSupply` past
   `cap` must have no effect. Minting up to exactly `cap` is allowed.
3. **Minting is exact.** A successful `mint(to, amount)` increases both
   `totalSupply` and the balance of `to` by exactly `amount`, and changes no
   other balance.
4. **Transfers are exact and conserve supply.** A successful
   `transfer(to, amount)` called by `sender` decreases the balance of `sender`
   by exactly `amount`, increases the balance of `to` by exactly `amount`
   (a transfer to oneself leaves that balance unchanged), changes no other
   balance, leaves `totalSupply` unchanged, and returns `true`.
5. **No overdraft.** A transfer of more than the sender's balance must have no
   effect.
6. **Owner and cap are fixed.** No call changes `owner` or `cap` after
   deployment.

## What a specification is for

The goal of a specification is **discriminating power**: it must separate this
token from faulty variants of it. Faulty variants of the token exist (for
example, versions that get one of the guarantees above wrong); a
specification is good to the extent that it is satisfied by the token as
described and violated by every faulty variant.

Making the checker pass is **not** the goal. A specification that the checker
accepts because it says little or nothing (for example, one whose conditions
can never be met, or whose conclusions are true of every contract) has no
value, however easily it is accepted. Weakening a specification until it is
accepted is the failure this exercise measures, not a solution to it.
