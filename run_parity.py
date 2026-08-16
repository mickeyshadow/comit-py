"""Run phase-A parity against the R export in the harness repo."""
from comitpy.parity import compare

PARITY_DIR = r"D:\comit-harness\results\parity"

if __name__ == "__main__":
    worst = compare(PARITY_DIR, PARITY_DIR + r"\r_primal.csv")
    print("\nworst tech-year deviations:")
    print(worst.head(10).to_string(index=False))
