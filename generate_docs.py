import shutil

shutil.copyfile("README.md", "README.md.bak")

readme_text = open("README.md").read()


def replace(readme_text, from_str, to_str, with_str):
    index_of_first = readme_text.find(from_str)
    if index_of_first == -1:
        raise Exception(f"Could not find '{from_str}' in README.md")
    index_of_last = readme_text.find(to_str, index_of_first + len(from_str))
    if index_of_last == -1:
        raise Exception(f"Could not find '{to_str}' in README.md after '{from_str}'")

    return readme_text[:index_of_first] + with_str + readme_text[index_of_last + len(to_str) :]


def get_help_text(cmd):
    import subprocess

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
    if result.returncode != 0:
        raise Exception(f"Command {cmd} failed with error: {result.stderr}")
    return result.stdout


def replace_in_readme(module, readme_text):

    pingdata_helptext = get_help_text(["python", "-m", f"pingintel_api.{module}_cmd", "--help"])
    pingdata_helptext = pingdata_helptext.replace(f"python -m pingintel_api.{module}_cmd", module)
    print(f"Replacing help text for {module}...")
    print(pingdata_helptext)

    readme_text = replace(
        readme_text,
        from_str=f"""```
Usage: {module}""",
        to_str="""```""",
        with_str=f"""```
{pingdata_helptext}
```""",
    )

    return readme_text


readme_text = replace_in_readme("sovfixerapi", readme_text)
readme_text = replace_in_readme("pingvisionapi", readme_text)
readme_text = replace_in_readme("pingmapsapi", readme_text)
readme_text = replace_in_readme("pingdataapi", readme_text)


open("README.md", "w").write(readme_text)
