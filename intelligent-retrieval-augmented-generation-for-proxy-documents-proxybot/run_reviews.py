from reviews.reviews import run_bandit

# Runs bandit on the current directory
run_bandit(test_path=".", output_format="html")
run_bandit(test_path=".", output_format="json")
