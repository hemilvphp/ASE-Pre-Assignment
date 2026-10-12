from datetime import datetime
import json
import re
import urllib.error
import urllib.request


def normalize(s):
  return re.sub(r"[-_.]+", "-", s).lower()


def audit_requirements(filepath="requirements.txt"):
  total_checked = 0
  not_on_pypi = []
  versions_not_on_pypi = []
  valid_releases = []  # Stores tuples of (name, version, upload_time)

  try:
    with open(filepath, "r", encoding="utf-8") as f:
      lines = f.readlines()
  except FileNotFoundError:
    print(f"Error: The file '{filepath}' was not found.")
    return

  for line in lines:
    line = line.strip()
    # Skip empty lines and comments
    if not line or line.startswith("#"):
      continue

    # We are looking for pinned requirements using '=='
    if "==" not in line:
      continue

    parts = line.split("==")
    pkg_part = parts[0].strip()
    version = parts[1].strip()

    # Handle extras like package[security]==1.0.0
    if "[" in pkg_part:
      pkg_name = pkg_part.split("[")[0].strip()
    else:
      pkg_name = pkg_part

    # Increment total checked immediately for every valid requirement line
    total_checked += 1

    url = f"https://pypi.org/pypi/{pkg_name.lower()}/json"

    try:
      req = urllib.request.Request(
          url, headers={"User-Agent": "RequirementAuditor/1.0"}
      )
      with urllib.request.urlopen(req) as response:
        final_url = response.url  # The URL after any redirects

        # If the redirected URL doesn't match the requested package name,
        # it means PyPI redirected a non-existent/normalized name.
        expected_path = f"/pypi/{normalize(pkg_name)}/json"
        if expected_path not in final_url:
          not_on_pypi.append(pkg_name)
          continue

        data = json.loads(response.read().decode("utf-8"))
        releases = data.get("releases", {})

        if version not in releases:
          versions_not_on_pypi.append(f"{pkg_name}=={version}")
        else:
          files = releases[version]
          if files and len(files) > 0:
            upload_time = files[0].get("upload_time")
            if upload_time:
              valid_releases.append((pkg_name, version, upload_time))

    except urllib.error.HTTPError as e:
      if e.code == 404:
        not_on_pypi.append(pkg_name)

  # Determine oldest pinned release
  oldest_formatted = "N/A"
  if valid_releases:
    # Sort by upload_time string (ISO-like format sorts chronologically)
    oldest = min(valid_releases, key=lambda x: x[2])
    name, ver, ut = oldest
    year = ut[:4]  # Extract year from upload_time
    oldest_formatted = f"{name}=={ver}({year})"

  # --- Print Required Outputs ---
  print("\n=== PyPI Requirement Audit Report ===")
  print(f"1. Dependencies checked: {total_checked}")
  print(f"2. Packages not on PyPI: {len(not_on_pypi)}")
  print(f"3. Versions not on PyPI: {len(versions_not_on_pypi)}")
  print(f"4. Oldest pinned release: {oldest_formatted}")


if __name__ == "__main__":
  audit_requirements()
  
  