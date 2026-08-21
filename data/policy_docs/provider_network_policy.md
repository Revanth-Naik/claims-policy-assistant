# Meridian Health Plan — Provider Network Policy

*Fictional plan document generated for a portfolio project. Not a real insurance product.*

## Network Tiers
Providers are credentialed into the Meridian network annually and assigned an **In-Network** or **Out-of-Network** status per region.

- **In-Network**: Contracted rate applies; member cost-sharing follows the standard copay/coinsurance schedule for their plan.
- **Out-of-Network**: PPO plans (Gold, Silver) reimburse at a reduced coinsurance rate and the provider may balance-bill the member for the difference between billed and allowed amounts. HMO plans (Bronze, Platinum) do not cover out-of-network care except emergencies as defined under federal no-surprises regulations.

## Credentialing & Network Changes
A provider's network status can change mid-year if their contract lapses or is terminated. When this happens, claims for dates of service *before* the status change use the provider's prior network status; claims for dates of service *after* the change use the new status. This is why provider network status must be tracked historically (Type 2 slowly changing dimension) rather than overwritten.

## Referral Requirements by Specialty
Referrals are required for all specialties under HMO plans except: Behavioral Health, OB/GYN, and Pediatrics (self-referral permitted). PPO plans do not require referrals for any specialty.
