from subprocess import call

import pytest

from piptools.lock import check, generate_locks, read_locks

pytestmark = pytest.mark.usefixtures("tmpdir_cwd")


def test_generate_locks():
    with open("requirements.in", "w") as req_in:
        req_in.write("Flask")

    locks = generate_locks("requirements.in")
    assert locks


def test_generate_locks_string_can_be_parsed_by_shasum():
    if call("shasum --help", shell=True) != 0:
        pytest.skip("requires working version of shasum UNIX script")

    with open("requirements.in", "w") as req_in:
        req_in.write("Flask")

    locks = generate_locks("requirements.in")

    with open("lock.sha256", "w") as f:
        f.write(locks["requirements.in"][7:])

    returncode = call("shasum -a 256 -c lock.sha256", shell=True)
    assert returncode == 0


def test_generate_locks_depends_on_requirements():
    with open("requirements.in", "w") as req_in:
        req_in.write("Flask")

    lock_flask = generate_locks("requirements.in")

    with open("requirements.in", "w") as req_in:
        req_in.write("Django")

    lock_django = generate_locks("requirements.in")

    assert lock_flask != lock_django


def test_generate_locks_depends_on_pip_options():
    with open("requirements.in", "w") as req_in:
        req_in.write("Flask")

    locks = generate_locks("requirements.in")

    with open("requirements.in", "w") as req_in:
        req_in.write("--pre\n")
        req_in.write("Flask")

    assert generate_locks("requirements.in") != locks


def test_generate_locks_includes_file_names():
    with open("requirements.in", "w") as req_in:
        req_in.write("Flask")

    locks = generate_locks("requirements.in")

    assert "requirements.in" in locks


def test_generate_locks_multiple_files():
    with open("requirements.in", "w") as req_in:
        req_in.write("Flask")
    with open("dev-requirements.in", "w") as req_in:
        req_in.write("pytest")

    locks = generate_locks("requirements.in", "dev-requirements.in")

    assert locks
    assert "requirements.in" in locks
    assert "dev-requirements.in" in locks


def test_generate_locks_multiple_files_ordered():
    with open("requirements.in", "w") as req_in:
        req_in.write("Flask")
    with open("dev-requirements.in", "w") as req_in:
        req_in.write("pytest")

    locks = generate_locks("requirements.in", "dev-requirements.in")

    assert list(locks.keys()) == ["requirements.in", "dev-requirements.in"]


def test_generate_locks_depends_on_included_requirements():
    with open("requirements.txt", "w") as req_in:
        req_in.write("Flask==1.1.1")
    with open("dev-requirements.in", "w") as req_in:
        req_in.write("-r requirements.txt\n")
        req_in.write("pytest")

    locks = generate_locks("dev-requirements.in")

    assert "requirements.txt" in locks


def test_generate_locks_depends_on_included_constraints():
    with open("constraints.txt", "w") as c_txt:
        c_txt.write("Django>2.0.0\n")
        c_txt.write("Flask>1.0.0")
    with open("requirements.in", "w") as req_in:
        req_in.write("-c constraints.txt\n")
        req_in.write("Flask")

    locks = generate_locks("requirements.in")

    assert "constraints.txt" in locks


def test_read_locks():
    with open("requirements.in", "w") as req_in:
        req_in.write("Flask")

    locks = generate_locks("requirements.in")

    with open("requirements.txt", "w") as req_txt:
        for lock in locks.values():
            req_txt.write(lock)

    assert read_locks("requirements.txt") == locks


def test_read_locks_empty_file():
    with open("requirements.txt", "w"):
        pass

    assert not read_locks("requirements.txt")


def test_read_locks_nonexistent_file():
    with pytest.raises(ValueError, match="No such file: 'requirements.txt'"):
        read_locks("requirements.txt")


def test_read_locks_commented():
    with open("requirements.in", "w") as req_in:
        req_in.write("Flask")

    locks = generate_locks("requirements.in")

    with open("requirements.txt", "w") as req_txt:
        for lock in locks.values():
            req_txt.write("#    {}".format(lock))

    assert read_locks("requirements.txt") == locks


def test_check():
    with open("requirements.in", "w") as req_in:
        req_in.write("Flask")

    locks = generate_locks("requirements.in")

    assert check(locks) is True


def test_check_empty_file():
    with open("requirements.txt", "w"):
        pass

    assert check(read_locks("requirements.txt")) is False


def test_check_none():
    assert check(None) is False


def test_check_depends_on_file_content():
    with open("requirements.in", "w") as req_in:
        req_in.write("Flask")

    lock_flask = generate_locks("requirements.in")

    with open("requirements.in", "w") as req_in:
        req_in.write("Django")

    assert check(lock_flask) is False


def test_check_multiple_files():
    with open("requirements.in", "w") as req_in:
        req_in.write("Flask")
    with open("dev-requirements.in", "w") as req_in:
        req_in.write("pytest")

    locks = generate_locks("requirements.in", "dev-requirements.in")

    assert check(locks) is True

    with open("requirements.in", "w") as req_in:
        req_in.write("Django")

    assert check(locks) is False


def test_lock_depends_on_included_requirements():
    with open("requirements.txt", "w") as req_in:
        req_in.write("Flask==1.1.1")
    with open("dev-requirements.in", "w") as req_in:
        req_in.write("-r requirements.txt\n")
        req_in.write("pytest")

    locks = generate_locks("dev-requirements.in")

    with open("requirements.txt", "w") as req_in:
        req_in.write("Flask==1.1.2")

    assert check(locks) is False


def test_check_depends_on_included_constraints():
    with open("constraints.txt", "w") as c_txt:
        c_txt.write("Django>2.0.0\n")
        c_txt.write("Flask>1.0.0")
    with open("requirements.in", "w") as req_in:
        req_in.write("-c constraints.txt\n")
        req_in.write("Flask")

    locks = generate_locks("requirements.in")

    with open("constraints.txt", "w") as c_txt:
        c_txt.write("Django>2.0.0,<2.2.1\n")
        c_txt.write("Flask>1.0.0")

    assert check(locks) is False
