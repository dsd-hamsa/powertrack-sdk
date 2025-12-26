import powertrack_sdk
import os
fetch_file = os.path.join(os.path.dirname(powertrack_sdk.__file__), 'mostRecentFetch.js')
print(fetch_file)  # Shows the path to edit