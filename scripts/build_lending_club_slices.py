"""Build the course credit-model files from the Lending Club loan data.

Source: the "All Lending Club loan data" collection on Kaggle (Nathan George, CC0 public domain),
https://www.kaggle.com/datasets/wordsforthewise/lending-club, which repackages the loan files
Lending Club published on its own site. The accepted-loans file holds 2,260,701 loans issued 2007 to
2018 with 151 columns. The download needs no Kaggle account:
https://www.kaggle.com/api/v1/datasets/download/wordsforthewise/lending-club (1.36 GB zip).

Population kept: 36-month loans issued 2012 to 2015 whose outcome is known (status Fully Paid or
Charged Off), with no blank in any model column and a home-ownership value of RENT, MORTGAGE, or OWN.
Every one of these loans had reached the end of its term when the file was published, so the
outcome column is complete for them. Loans issued later are left out on purpose: many were still
being repaid when the file was made, and a file that mixes finished and unfinished loans makes the
newest loans look safer than they are.

Outputs (into student/credit/):
  loans.csv          5,000 loans with the outcome, for class
  new_loans.csv      1,000 loans with the outcome and the post-outcome column removed, for scoring
  loans_project.csv  50,000 loans with the outcome, for the project
and, next to the zip (never published): new_loans_outcomes.csv, the outcomes of the 1,000.

Usage: uv run python -I scripts/build_lending_club_slices.py <path to lending-club.zip> <repo root>
"""
import os
import sys
import zipfile

import numpy as np
import pandas as pd

SEED = 2026
CLASS_ROWS, NEW_ROWS, PROJECT_ROWS = 5_000, 1_000, 50_000

RENAME = {
    "id": "loan_id",
    "loan_amnt": "loan_amount",
    "int_rate": "interest_rate",
    "annual_inc": "annual_income",
    "dti": "dti",
    "delinq_2yrs": "late_payments_2y",
    "inq_last_6mths": "inquiries_6m",
    "open_acc": "open_accounts",
    "pub_rec": "public_records",
    "revol_bal": "revolving_balance",
    "revol_util": "card_utilization",
    "total_acc": "total_accounts",
    "home_ownership": "home_ownership",
    "purpose": "purpose",
    "addr_state": "state",
}
MODEL_COLUMNS = [
    "loan_amount", "interest_rate", "annual_income", "dti", "credit_score", "late_payments_2y",
    "inquiries_6m", "open_accounts", "public_records", "revolving_balance", "card_utilization",
    "total_accounts", "employment_years",
]
FINAL = (["loan_id"] + MODEL_COLUMNS
         + ["home_ownership", "purpose", "state", "issue_year", "last_credit_score", "default"])


def employment_years(text):
    if pd.isna(text):
        return np.nan
    text = str(text)
    if text.startswith("<"):
        return 0.0
    return float(text.split()[0].rstrip("+"))


def main(zip_path, repo_root):
    out_dir = os.path.join(repo_root, "student", "credit")
    os.makedirs(out_dir, exist_ok=True)
    z = zipfile.ZipFile(zip_path)
    member = [n for n in z.namelist() if n.endswith(".csv") and n.startswith("accepted")]
    member = [n for n in member if "/" in n][0] if any("/" in n for n in member) else member[0]
    usecols = list(RENAME) + ["term", "issue_d", "loan_status", "emp_length", "fico_range_low",
                              "fico_range_high", "last_fico_range_low", "last_fico_range_high"]
    with z.open(member) as fh:
        raw = pd.read_csv(fh, usecols=usecols, low_memory=False)
    print("accepted loans read:", len(raw))

    raw["issue_year"] = pd.to_datetime(raw["issue_d"], format="%b-%Y", errors="coerce").dt.year
    raw["term"] = raw["term"].str.strip()
    finished = raw["loan_status"].isin(["Fully Paid", "Charged Off"])

    # the year trap, on every 36-month loan (reading and lab quote these)
    m36 = raw[raw["term"] == "36 months"]
    by_year = m36.groupby("issue_year").agg(
        loans=("loan_status", "size"),
        finished=("loan_status", lambda s: s.isin(["Fully Paid", "Charged Off"]).mean()),
        charged_off_share=("loan_status", lambda s: (s == "Charged Off").mean()),
    )
    fin = m36[finished.loc[m36.index]]
    by_year["default_rate_among_finished"] = fin.groupby("issue_year")["loan_status"].apply(
        lambda s: (s == "Charged Off").mean())
    print("36-month loans by issue year:")
    print(by_year.round(3).to_string())

    pop = m36[finished.loc[m36.index] & m36["issue_year"].between(2012, 2015)].copy()
    pop = pop.rename(columns=RENAME)
    pop["credit_score"] = ((pop["fico_range_low"] + pop["fico_range_high"]) / 2).round().astype("Int64")
    pop["last_credit_score"] = ((pop["last_fico_range_low"] + pop["last_fico_range_high"]) / 2).round()
    pop["employment_years"] = pop["emp_length"].map(employment_years)
    pop["default"] = (pop["loan_status"] == "Charged Off").astype(int)
    pop = pop[pop["home_ownership"].isin(["RENT", "MORTGAGE", "OWN"])]
    before = len(pop)
    pop = pop.dropna(subset=MODEL_COLUMNS + ["last_credit_score"])
    print(f"population 36-month 2012-2015 finished: {before}; after dropping blanks: {len(pop)}; "
          f"default rate {pop['default'].mean():.4f}")
    pop = pop[FINAL].astype({"loan_id": "int64", "last_credit_score": "int64"})
    for c in ["late_payments_2y", "inquiries_6m", "open_accounts", "public_records", "total_accounts",
              "employment_years", "revolving_balance", "loan_amount"]:
        pop[c] = pop[c].astype("int64")

    rng = np.random.default_rng(SEED)
    order = rng.permutation(len(pop))
    pop = pop.iloc[order].reset_index(drop=True)
    loans = pop.iloc[:CLASS_ROWS]
    new = pop.iloc[CLASS_ROWS:CLASS_ROWS + NEW_ROWS]
    project = pop.iloc[CLASS_ROWS + NEW_ROWS:CLASS_ROWS + NEW_ROWS + PROJECT_ROWS]

    loans.to_csv(os.path.join(out_dir, "loans.csv"), index=False)
    new.drop(columns=["last_credit_score", "default"]).to_csv(os.path.join(out_dir, "new_loans.csv"), index=False)
    project.to_csv(os.path.join(out_dir, "loans_project.csv"), index=False)
    new[["loan_id", "last_credit_score", "default"]].to_csv(
        os.path.join(os.path.dirname(zip_path), "new_loans_outcomes.csv"), index=False)
    for name, df in [("loans.csv", loans), ("new_loans.csv", new), ("loans_project.csv", project)]:
        print(f"{name}: {len(df)} rows, default rate {df['default'].mean():.4f}, "
              f"{os.path.getsize(os.path.join(out_dir, name)) / 1e6:.2f} MB")
    print("Arkansas loans in the population:", int((pop['state'] == 'AR').sum()),
          "default rate", round(pop.loc[pop['state'] == 'AR', 'default'].mean(), 4))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
