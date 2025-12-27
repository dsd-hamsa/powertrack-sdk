# The below allows for importing a mock client for testing purposes from the examples directory.
# In production, you would import your client from the actual SDK package.

import powertrack_sdk
import os
fetch_file = os.path.join(os.path.dirname(powertrack_sdk.__file__), 'mostRecentFetch.js')
print(fetch_file)  # Shows the path to edit