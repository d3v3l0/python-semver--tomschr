"""Version handling."""

import collections
import re
from functools import wraps
from typing import (
    Any,
    Callable,
    Collection,
    Dict,
    Iterable,
    List,
    Optional,
    SupportsInt,
    Tuple,
    Union,
    cast,
)

from ._types import (
    String,
    StringOrInt,
    VersionDict,
    VersionIterator,
    VersionPart,
    VersionTuple,
)

# These types are required here because of circular imports
Comparable = Union["Version", Dict[str, VersionPart], Collection[VersionPart], String]
Comparator = Callable[["Version", Comparable], bool]


def _comparator(operator: Comparator) -> Comparator:
    """Wrap a Version binary op method in a type-check."""

    @wraps(operator)
    def wrapper(self: "Version", other: Comparable) -> bool:
        comparable_types = (
            Version,
            dict,
            tuple,
            list,
            *String.__args__,  # type: ignore
        )
        if not isinstance(other, comparable_types):
            return NotImplemented
        return operator(self, other)

    return wrapper


def _cmp(a, b):  # TODO: type hints
    """Return negative if a<b, zero if a==b, positive if a>b."""
    return (a > b) - (a < b)


class Version:
    """
    A semver compatible version class.

    :param args: a tuple with version information. It can consist of:

        * a maximum length of 5 items that comprehend the major,
          minor, patch, prerelease, or build parts.
        * a str or bytes string at first position that contains a valid semver
          version string.
    :param major: version when you make incompatible API changes.
    :param minor: version when you add functionality in
                  a backwards-compatible manner.
    :param patch: version when you make backwards-compatible bug fixes.
    :param prerelease: an optional prerelease string
    :param build: an optional build string

    This gives you some options to call the :class:`Version` class.
    Precedence has the keyword arguments over the positional arguments.

    >>> Version(1, 2, 3)
    Version(major=1, minor=2, patch=3, prerelease=None, build=None)
    >>> Version("2.3.4-pre.2")
    Version(major=2, minor=3, patch=4, prerelease="pre.2", build=None)
    >>> Version(major=2, minor=3, patch=4, build="build.2")
    Version(major=2, minor=3, patch=4, prerelease=None, build="build.2")
    """

    #: The name of the version parts
    VERSIONPARTS: Tuple[str] = ("major", "minor", "patch", "prerelease", "build")
    #: The default values for each part (position match with ``VERSIONPARTS``):
    VERSIONPARTDEFAULTS: VersionTuple = (0, 0, 0, None, None)
    #: The allowed types for each part (position match with ``VERSIONPARTS``):
    ALLOWED_TYPES = (
        (int, str, bytes),  # major
        (int, str, bytes),  # minor
        (int, str, bytes),  # patch
        (int, str, bytes, type(None)),  # prerelease
        (int, str, bytes, type(None)),  # build
    )

    __slots__ = ("_major", "_minor", "_patch", "_prerelease", "_build")
    #: Regex for number in a prerelease
    _LAST_NUMBER = re.compile(r"(?:[^\d]*(\d+)[^\d]*)+")
    #: Regex for a semver version
    _REGEX = re.compile(
        r"""
            ^
            (?P<major>0|[1-9]\d*)
            \.
            (?P<minor>0|[1-9]\d*)
            \.
            (?P<patch>0|[1-9]\d*)
            (?:-(?P<prerelease>
                (?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)
                (?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*
            ))?
            (?:\+(?P<build>
                [0-9a-zA-Z-]+
                (?:\.[0-9a-zA-Z-]+)*
            ))?
            $
        """,
        re.VERBOSE,
    )

    def _check_types(self, *args: Tuple) -> List[bool]:
        """
        Check if the given arguments conform to the types in ``ALLOWED_TYPES``.

        :return: bool for each position
        """
        cls = self.__class__
        return [
            isinstance(item, expected_type)
            for item, expected_type in zip(args, cls.ALLOWED_TYPES)
        ]

    def _raise_if_args_are_invalid(self, *args):
        """
        Checks conditions for positional arguments. For example:

        * No more than 5 arguments.
        * If first argument  is a string, contains a dot, and there
          are more arguments.
        * Arguments have invalid types.

        :raises ValueError: if more arguments than 5 or if first argument
           is a string, contains a dot, and there are more arguments.
        :raises TypeError: if there are invalid types.
        """
        if args and len(args) > 5:
            raise ValueError("You cannot pass more than 5 arguments to Version")
        elif len(args) > 1 and "." in str(args[0]):
            raise ValueError(
                "You cannot pass a string and additional positional arguments"
            )
        types_in_args = self._check_types(*args)
        if not all(types_in_args):
            pos = types_in_args.index(False)
            raise TypeError(
                "not expecting type in argument position "
                f"{pos} (type: {type(args[pos])})"
            )

    def __init__(
        self,
        *args: Tuple[
            StringOrInt,  # major
            Optional[StringOrInt],  # minor
            Optional[StringOrInt],  # patch
            Optional[StringOrInt],  # prerelease
            Optional[StringOrInt],  # build
        ],
        # *,
        major: SupportsInt = None,
        minor: SupportsInt = None,
        patch: SupportsInt = None,
        prerelease: StringOrInt = None,
        build: StringOrInt = None,
    ):
        #
        # The algorithm to support different Version calls is this:
        #
        # 1. Check first, if there are invalid calls. For example
        #    more than 5 items in args or a unsupported combination
        #    of args and version part arguments (major, minor, etc.)
        #    If yes, raise an exception.
        #
        # 2. Create a dictargs dict:
        #    a. If the first argument is a version string which contains
        #       a dot it's likely it's a semver string. Try to convert
        #       them into a dict and save it to dictargs.
        #    b. If the first argument is not a version string, try to
        #       create the dictargs from the args argument.
        #
        # 3. Create a versiondict from the version part arguments.
        #    This contains only items if the argument is not None.
        #
        # 4. Merge the two dicts, versiondict overwrites dictargs.
        #    In other words, if the user specifies Version(1, major=2)
        #    the major=2 has precedence over the 1.
        #
        # 5. Set all version components from versiondict. If the key
        #    doesn't exist, set a default value.

        cls = self.__class__
        # (1) check combinations and types
        self._raise_if_args_are_invalid(*args)

        # (2) First argument was a string
        if args and args[0] and "." in cls._enforce_str(args[0]):  # type: ignore
            dictargs = cls._parse(cast(String, args[0]))
        else:
            dictargs = dict(zip(cls.VERSIONPARTS, args))

        # (3) Only include part in versiondict if value is not None
        versiondict = {
            part: value
            for part, value in zip(
                cls.VERSIONPARTS, (major, minor, patch, prerelease, build)
            )
            if value is not None
        }

        # (4) Order here is important: versiondict overwrites dictargs
        versiondict = {**dictargs, **versiondict}  # type: ignore

        # (5) Set all version components:
        self._major = cls._ensure_int(
            cast(StringOrInt, versiondict.get("major", cls.VERSIONPARTDEFAULTS[0]))
        )
        self._minor = cls._ensure_int(
            cast(StringOrInt, versiondict.get("minor", cls.VERSIONPARTDEFAULTS[1]))
        )
        self._patch = cls._ensure_int(
            cast(StringOrInt, versiondict.get("patch", cls.VERSIONPARTDEFAULTS[2]))
        )
        self._prerelease = cls._enforce_str(
            cast(
                Optional[StringOrInt],
                versiondict.get("prerelease", cls.VERSIONPARTDEFAULTS[3]),
            )
        )
        self._build = cls._enforce_str(
            cast(
                Optional[StringOrInt],
                versiondict.get("build", cls.VERSIONPARTDEFAULTS[4]),
            )
        )

    @classmethod
    def _nat_cmp(cls, a, b):  # TODO: type hints
        def cmp_prerelease_tag(a, b):
            if isinstance(a, int) and isinstance(b, int):
                return _cmp(a, b)
            elif isinstance(a, int):
                return -1
            elif isinstance(b, int):
                return 1
            else:
                return _cmp(a, b)

        a, b = a or "", b or ""
        a_parts, b_parts = a.split("."), b.split(".")
        a_parts = [int(x) if re.match(r"^\d+$", x) else x for x in a_parts]
        b_parts = [int(x) if re.match(r"^\d+$", x) else x for x in b_parts]
        for sub_a, sub_b in zip(a_parts, b_parts):
            cmp_result = cmp_prerelease_tag(sub_a, sub_b)
            if cmp_result != 0:
                return cmp_result
        else:
            return _cmp(len(a), len(b))

    @classmethod
    def _ensure_int(cls, value: StringOrInt) -> int:
        """
        Ensures integer value type regardless if argument type is str or bytes.
        Otherwise raise ValueError.

        :param value:
        :raises ValueError: Two conditions:
          * If value is not an integer or cannot be converted.
          * If value is negative.
        :return: the converted value as integer
        """
        try:
            value = int(value)
        except ValueError:
            raise ValueError(
                "Expected integer or integer string for major, minor, or patch"
            )

        if value < 0:
            raise ValueError(
                f"Argument {value} is negative. A version can only be positive."
            )
        return value

    @classmethod
    def _enforce_str(cls, s: Optional[StringOrInt]) -> Optional[str]:
        """
        Forces input to be string, regardless of int, bytes, or string.

        :param s: a string, integer or None
        :return: a Unicode string (or None)
        """
        if isinstance(s, int):
            return str(s)
        return cls._ensure_str(s)

    @classmethod
    def _ensure_str(cls, s: Optional[String], encoding="UTF-8") -> Optional[str]:
        """
        Ensures string type regardless if argument type is str or bytes.

        :param s: the string (or None)
        :param encoding: the encoding, default to "UTF-8"
        :return: a Unicode string (or None)
        """
        if isinstance(s, bytes):
            return cast(str, s.decode(encoding))
        return s

    @classmethod
    def _parse(cls, version: String) -> Dict:
        """
        Parse version string and return version parts.

        :param version: version string
        :return: a dictionary with version parts
        :raises ValueError: if version is invalid
        :raises TypeError: if version contains unexpected type

        >>> semver.Version.parse('3.4.5-pre.2+build.4')
        Version(major=3, minor=4, patch=5, prerelease='pre.2', build='build.4')
        """
        version = cast(str, cls._ensure_str(version))
        if not isinstance(version, String.__args__):  # type: ignore
            raise TypeError(f"not expecting type {type(version)!r}")
        match = cls._REGEX.match(version)
        if match is None:
            raise ValueError(f"{version!r} is not valid SemVer string")

        return cast(dict, match.groupdict())

    @property
    def major(self) -> int:
        """The major part of a version (read-only)."""
        return self._major

    @major.setter
    def major(self, value):
        raise AttributeError("attribute 'major' is readonly")

    @property
    def minor(self) -> int:
        """The minor part of a version (read-only)."""
        return self._minor

    @minor.setter
    def minor(self, value):
        raise AttributeError("attribute 'minor' is readonly")

    @property
    def patch(self) -> int:
        """The patch part of a version (read-only)."""
        return self._patch

    @patch.setter
    def patch(self, value):
        raise AttributeError("attribute 'patch' is readonly")

    @property
    def prerelease(self) -> Optional[str]:
        """The prerelease part of a version (read-only)."""
        return self._prerelease

    @prerelease.setter
    def prerelease(self, value):
        raise AttributeError("attribute 'prerelease' is readonly")

    @property
    def build(self) -> Optional[str]:
        """The build part of a version (read-only)."""
        return self._build

    @build.setter
    def build(self, value):
        raise AttributeError("attribute 'build' is readonly")

    def to_tuple(self) -> VersionTuple:
        """
        Convert the Version object to a tuple.

        .. versionadded:: 2.10.0
           Renamed ``VersionInfo._astuple`` to ``VersionInfo.to_tuple`` to
           make this function available in the public API.

        :return: a tuple with all the parts

        >>> semver.Version(5, 3, 1).to_tuple()
        (5, 3, 1, None, None)
        """
        return (self.major, self.minor, self.patch, self.prerelease, self.build)

    def to_dict(self) -> VersionDict:
        """
        Convert the Version object to an OrderedDict.

        .. versionadded:: 2.10.0
           Renamed ``VersionInfo._asdict`` to ``VersionInfo.to_dict`` to
           make this function available in the public API.

        :return: an OrderedDict with the keys in the order ``major``, ``minor``,
          ``patch``, ``prerelease``, and ``build``.

        >>> semver.Version(3, 2, 1).to_dict()
        OrderedDict([('major', 3), ('minor', 2), ('patch', 1), ('prerelease', None), ('build', None)])  # noqa: E501
        """
        return collections.OrderedDict(
            (
                ("major", self.major),
                ("minor", self.minor),
                ("patch", self.patch),
                ("prerelease", self.prerelease),
                ("build", self.build),
            )
        )

    def __iter__(self) -> VersionIterator:
        """Return iter(self)."""
        yield from self.to_tuple()

    @staticmethod
    def _increment_string(string: str) -> str:
        """
        Look for the last sequence of number(s) in a string and increment.

        :param string: the string to search for.
        :return: the incremented string

        Source:
        http://code.activestate.com/recipes/442460-increment-numbers-in-a-string/#c1
        """
        match = Version._LAST_NUMBER.search(string)
        if match:
            next_ = str(int(match.group(1)) + 1)
            start, end = match.span(1)
            string = string[: max(end - len(next_), start)] + next_ + string[end:]
        return string

    def bump_major(self) -> "Version":
        """
        Raise the major part of the version, return a new object but leave self
        untouched.

        :return: new object with the raised major part

        >>> semver.Version("3.4.5").bump_major()
        Version(major=4, minor=0, patch=0, prerelease=None, build=None)
        """
        cls = type(self)
        return cls(major=self._major + 1)

    def bump_minor(self) -> "Version":
        """
        Raise the minor part of the version, return a new object but leave self
        untouched.

        :return: new object with the raised minor part

        >>> semver.Version("3.4.5").bump_minor()
        Version(major=3, minor=5, patch=0, prerelease=None, build=None)
        """
        cls = type(self)
        return cls(major=self._major, minor=self._minor + 1)

    def bump_patch(self) -> "Version":
        """
        Raise the patch part of the version, return a new object but leave self
        untouched.

        :return: new object with the raised patch part

        >>> semver.Version("3.4.5").bump_patch()
        Version(major=3, minor=4, patch=6, prerelease=None, build=None)
        """
        cls = type(self)
        return cls(major=self._major, minor=self._minor, patch=self._patch + 1)

    def bump_prerelease(self, token: str = "rc") -> "Version":
        """
        Raise the prerelease part of the version, return a new object but leave
        self untouched.

        :param token: defaults to ``rc``
        :return: new object with the raised prerelease part

        >>> semver.Version("3.4.5").bump_prerelease()
        Version(major=3, minor=4, patch=5, prerelease='rc.2', build=None)  # noqa: E501
        """
        cls = type(self)
        prerelease = cls._increment_string(self._prerelease or (token or "rc") + ".0")
        return cls(
            major=self._major,
            minor=self._minor,
            patch=self._patch,
            prerelease=prerelease,
        )

    def bump_build(self, token: str = "build") -> "Version":
        """
        Raise the build part of the version, return a new object but leave self
        untouched.

        :param token: defaults to ``build``
        :return: new object with the raised build part

        >>> semver.Version("3.4.5-rc.1+build.9").bump_build()
        Version(major=3, minor=4, patch=5, prerelease='rc.1', build='build.10')  # noqa: E501
        """
        cls = type(self)
        build = cls._increment_string(self._build or (token or "build") + ".0")
        return cls(
            major=self._major,
            minor=self._minor,
            patch=self._patch,
            prerelease=self._prerelease,
            build=build,
        )

    def compare(self, other: Comparable) -> int:
        """
        Compare self with other.

        :param other: the second version
        :return: The return value is negative if ver1 < ver2,
             zero if ver1 == ver2 and strictly positive if ver1 > ver2

        >>> semver.Version("1.0.0").compare("2.0.0")
        -1
        >>> semver.Version("1.0.0").compare("1.0.0")
        0
        >>> semver.Version("1.0.0").compare("0.1.0")
        -1
        >>> semver.Version("2.0.0").compare(dict(major=2, minor=0, patch=0))
        0
        """
        cls = type(self)

        # See https://github.com/python/mypy/issues/4019
        if isinstance(other, String.__args__):  # type: ignore
            if "." not in cast(str, cls._ensure_str(other)):
                raise ValueError("Expected semver version string.")
            other = cls(other)
        elif isinstance(other, dict):
            other = cls(**other)
        elif isinstance(other, (tuple, list)):
            other = cls(*other)
        elif not isinstance(other, cls):
            raise TypeError(
                f"Expected str, bytes, dict, tuple, list, or {cls.__name__} instance, "
                f"but got {type(other)}"
            )

        v1 = self.to_tuple()[:3]
        v2 = other.to_tuple()[:3]
        x = _cmp(v1, v2)
        if x:
            return x

        rc1, rc2 = self.prerelease, other.prerelease
        rccmp = self._nat_cmp(rc1, rc2)

        if not rccmp:
            return 0
        if not rc1:
            return 1
        elif not rc2:
            return -1

        return rccmp

    def next_version(self, part: str, prerelease_token: str = "rc") -> "Version":
        """
        Determines next version, preserving natural order.

        .. versionadded:: 2.10.0

        This function is taking prereleases into account.
        The "major", "minor", and "patch" raises the respective parts like
        the ``bump_*`` functions. The real difference is using the
        "preprelease" part. It gives you the next patch version of the
        prerelease, for example:

        :param part: One of "major", "minor", "patch", or "prerelease"
        :param prerelease_token: prefix string of prerelease, defaults to 'rc'
        :return: new object with the appropriate part raised

        >>> str(semver.Version("0.1.4").next_version("prerelease"))
        '0.1.5-rc.1'
        """
        validparts = {
            "major",
            "minor",
            "patch",
            "prerelease",
            # "build", # currently not used
        }
        if part not in validparts:
            raise ValueError(
                "Invalid part. Expected one of {validparts}, but got {part!r}".format(
                    validparts=validparts, part=part
                )
            )
        version = self
        if (version.prerelease or version.build) and (
            part == "patch"
            or (part == "minor" and version.patch == 0)
            or (part == "major" and version.minor == version.patch == 0)
        ):
            return version.replace(prerelease=None, build=None)

        if part in ("major", "minor", "patch"):
            return getattr(version, "bump_" + part)()

        if not version.prerelease:
            version = version.bump_patch()
        return version.bump_prerelease(prerelease_token)

    @_comparator
    def __eq__(self, other: Comparable) -> bool:  # type: ignore
        return self.compare(other) == 0

    @_comparator
    def __ne__(self, other: Comparable) -> bool:  # type: ignore
        return self.compare(other) != 0

    @_comparator
    def __lt__(self, other: Comparable) -> bool:
        return self.compare(other) < 0

    @_comparator
    def __le__(self, other: Comparable) -> bool:
        return self.compare(other) <= 0

    @_comparator
    def __gt__(self, other: Comparable) -> bool:
        return self.compare(other) > 0

    @_comparator
    def __ge__(self, other: Comparable) -> bool:
        return self.compare(other) >= 0

    def __getitem__(
        self, index: Union[int, slice]
    ) -> Union[int, Optional[str], Tuple[Union[int, str], ...]]:
        """
        self.__getitem__(index) <==> self[index] Implement getitem.

        If the part  requested is undefined, or a part of the range requested
        is undefined, it will throw an index error.
        Negative indices are not supported.

        :param index: a positive integer indicating the
               offset or a :func:`slice` object
        :raises IndexError: if index is beyond the range or a part is None
        :return: the requested part of the version at position index

        >>> ver = semver.Version("3.4.5")
        >>> ver[0], ver[1], ver[2]
        (3, 4, 5)
        """
        if isinstance(index, int):
            index = slice(index, index + 1)
        index = cast(slice, index)

        if (
            isinstance(index, slice)
            and (index.start is not None and index.start < 0)
            or (index.stop is not None and index.stop < 0)
        ):
            raise IndexError("Version index cannot be negative")

        part = tuple(
            filter(lambda p: p is not None, cast(Iterable, self.to_tuple()[index]))
        )

        if len(part) == 1:
            return part[0]
        elif not part:
            raise IndexError("Version part undefined")
        return part

    def __repr__(self) -> str:
        s = ", ".join("%s=%r" % (key, val) for key, val in self.to_dict().items())
        return "%s(%s)" % (type(self).__name__, s)

    def __str__(self) -> str:
        version = f"{self.major:d}.{self.minor:d}.{self.patch:d}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __hash__(self) -> int:
        return hash(self.to_tuple()[:4])

    def finalize_version(self) -> "Version":
        """
        Remove any prerelease and build metadata from the version.

        :return: a new instance with the finalized version string

        >>> str(semver.Version('1.2.3-rc.5').finalize_version())
        '1.2.3'
        """
        cls = type(self)
        return cls(major=self.major, minor=self.minor, patch=self.patch)

    def match(self, match_expr: str) -> bool:
        """
        Compare self to match a match expression.

        :param match_expr: operator and version; valid operators are
              ``<```   smaller than
              ``>``   greater than
              ``>=``  greator or equal than
              ``<=``  smaller or equal than
              ``==``  equal
              ``!=``  not equal
        :return: True if the expression matches the version, otherwise False

        >>> semver.Version("2.0.0").match(">=1.0.0")
        True
        >>> semver.Version("1.0.0").match(">1.0.0")
        False
        """
        prefix = match_expr[:2]
        if prefix in (">=", "<=", "==", "!="):
            match_version = match_expr[2:]
        elif prefix and prefix[0] in (">", "<"):
            prefix = prefix[0]
            match_version = match_expr[1:]
        else:
            raise ValueError(
                "match_expr parameter should be in format <op><ver>, "
                "where <op> is one of "
                "['<', '>', '==', '<=', '>=', '!=']. "
                "You provided: %r" % match_expr
            )

        possibilities_dict = {
            ">": (1,),
            "<": (-1,),
            "==": (0,),
            "!=": (-1, 1),
            ">=": (0, 1),
            "<=": (-1, 0),
        }

        possibilities = possibilities_dict[prefix]
        cmp_res = self.compare(match_version)

        return cmp_res in possibilities

    @classmethod
    def parse(cls, version: String) -> "Version":
        """
        Parse version string to a Version instance.

        .. versionchanged:: 2.11.0
           Changed method from static to classmethod to
           allow subclasses.

        :param version: version string
        :return: a new :class:`Version` instance
        :raises ValueError: if version is invalid
        :raises TypeError: if version contains the wrong type

        >>> semver.Version('3.4.5-pre.2+build.4')
        Version(major=3, minor=4, patch=5, prerelease='pre.2', build='build.4')  # noqa: E501
        """
        matched_version_parts: Dict[str, Any] = cls._parse(version)
        return cls(**matched_version_parts)

    def replace(self, **parts: Union[int, Optional[str]]) -> "Version":
        """
        Replace one or more parts of a version and return a new
        :class:`Version` object, but leave self untouched

        .. versionadded:: 2.9.0
           Added :func:`Version.replace`

        :param parts: the parts to be updated. Valid keys are:
          ``major``, ``minor``, ``patch``, ``prerelease``, or ``build``
        :return: the new :class:`Version` object with the changed
          parts
        :raises TypeError: if ``parts`` contain invalid keys
        """
        version = self.to_dict()
        version.update(parts)
        try:
            return Version(**version)  # type: ignore
        except TypeError:
            unknownkeys = set(parts) - set(self.to_dict())
            error = "replace() got %d unexpected keyword argument(s): %s" % (
                len(unknownkeys),
                ", ".join(unknownkeys),
            )
            raise TypeError(error)

    @classmethod
    def isvalid(cls, version: str) -> bool:
        """
        Check if the string is a valid semver version.

        .. versionadded:: 2.9.1

        :param version: the version string to check
        :return: True if the version string is a valid semver version, False
                 otherwise.
        """
        try:
            cls.parse(version)
            return True
        except ValueError:
            return False


#: Keep the VersionInfo name for compatibility
VersionInfo = Version
