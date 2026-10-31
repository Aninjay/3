import os

# The API test fixtures seed the demo dataset (demo organizer/volunteer
# accounts and the Kala Fest pilot event). seed_database() only installs
# that data when SEED_DEMO_DATA is enabled, so default it on for the test
# session; an explicit environment value still wins.
os.environ.setdefault("SEED_DEMO_DATA", "true")
