%{?scl:%scl_package libstemmer}
%{!?scl:%global pkg_name %{name}}

%global		pre_release		.rc0
%global		major			38

Summary:	JavaScript interpreter and libraries
Name:		%{?scl_prefix}mozjs38
Version:	%{major}.2.1
Release:	9%{?dist}
License:	MPLv2.0 and BSD and GPLv2+ and GPLv3+ and LGPLv2.1 and LGPLv2.1+ and AFL and ASL 2.0
URL:		https://developer.mozilla.org/en-US/docs/Mozilla/Projects/SpiderMonkey/Releases/38
Source0:	https://people.mozilla.org/~sstangl/mozjs-%{version}%{pre_release}.tar.bz2

# According to mozilla devs x86_64 is the only 64-bit architecture. I tend to not agree with them.
Patch0:	fix-64bit-archs.patch
# same issue on s390 as in XUL/FF - https://bugzilla.redhat.com/show_bug.cgi?id=1219542
Patch1:	rhbz-1219542-s390-build.patch

BuildRequires:	pkgconfig(icu-i18n)
BuildRequires:	pkgconfig(nspr)
BuildRequires:	pkgconfig(libffi)
BuildRequires:	pkgconfig(zlib)
BuildRequires:	readline-devel
BuildRequires:	/usr/bin/zip
BuildRequires:	python-devel

%{?scl:Requires:%scl_runtime}

%description
JavaScript is the Netscape-developed object scripting language used in millions
of web pages and server applications worldwide. Netscape's JavaScript is a
super set of the ECMA-262 Edition 3 (ECMAScript) standard scripting language,
with only mild differences from the published standard.

%package devel
Summary: Header files, libraries and development documentation for %{name}
Group: Development/Libraries
Requires: %{name}%{?_isa} = %{version}-%{release}

%{?scl:Requires:%scl_runtime}

# Filtering provides without scl name
# https://fedoraproject.org/wiki/Packaging:AutoProvidesAndRequiresFiltering
%global __provides_exclude pkgconfig\\(

%description devel
This package contains the header files, static libraries and development
documentation for %{name}. If you like to develop programs using %{name},
you will need to install %{name}-devel.

%prep
%setup -q -n mozjs-%{major}.0.0/js/src
%patch0 -p1
%ifarch s390
%patch1 -p3 -b .rhbz-1219542-s390
%endif

%if 0%{?fedora} > 22
# Correct failed to link tests due to hardened build
sed -i 's|"-O2"|"-O2 -fPIC"|' configure
%endif

# Remove zlib directory (to be sure using system version)
rm -rf ../../modules/zlib

# Fix release number
head -n -1 ../../config/milestone.txt > ../../config/milestone.txt
echo "%{version}%{pre_release}" >> ../../config/milestone.txt

# Make mozjs these functions visible:
# JS::UTF8CharsToNewTwoByteCharsZ and JS::LossyUTF8CharsToNewTwoByteCharsZ
sed -i 's|^\(TwoByteCharsZ\)$|JS_PUBLIC_API\(\1\)|g' vm/CharacterEncoding.cpp
sed -i 's|^extern\ \(TwoByteCharsZ\)$|JS_PUBLIC_API\(\1\)|g' ../public/CharacterEncoding.h
# Also make visible js::DisableExtraThreads()
sed -i '/^void$/{$!{N;s/^\(void\)\n\(js\:\:DisableExtraThreads()\)$/JS_PUBLIC_API\(\1\)\n\2/;ty;P;D;:y}}'  vm/Runtime.cpp
sed -i 's|\(void\) \(DisableExtraThreads()\)|JS_PUBLIC_API\(\1\) \2|g'  vm/Runtime.h

# prefix major number in soname with sclname
sed -i -r 's|(MOZJS_MAJOR_VERSION=)|\1%{?scl_prefix}|g' configure

%build
# Need -fpermissive due to some macros using nullptr as bool false
export CFLAGS="%{optflags} -fpermissive"
export CXXFLAGS="$CFLAGS"
export PYTHON=/usr/bin/python2

%configure \
	--with-system-nspr \
	--enable-threadsafe \
	--enable-readline \
	--enable-xterm-updates \
	--enable-shared-js \
	--enable-gcgenerational \
	--enable-optimize \
	--with-system-zlib \
	--enable-system-ffi \
	--with-system-icu \
	--without-intl-api \
	--enable-pie

# prefix major number in soname with sclname
prefix=%{?scl_prefix}
sed -i -r "s|(libmozjs-38.so)|\1.${prefix%%-}|g" js/src/backend.mk

make %{?_smp_mflags}

%install
make install DESTDIR=%{buildroot}

mv %{buildroot}%{_libdir}/pkgconfig/js.pc %{buildroot}%{_libdir}/pkgconfig/mozjs-%{major}.pc
chmod a-x  %{buildroot}%{_libdir}/pkgconfig/*.pc

# Do not install binaries or static libraries
rm -f %{buildroot}%{_libdir}/*.a %{buildroot}%{_libdir}/*.ajs %{buildroot}%{_bindir}/js*

# Install files, not symlinks to build directory
pushd %{buildroot}%{_includedir}
    for link in `find . -type l`; do
	header=`readlink $link`
	rm -f $link
	cp -p $header $link
    done
popd
cp -p js/src/js-config.h %{buildroot}%{_includedir}/mozjs-%{major}

# Create symbolic link for devel subpackage
prefix=%{?scl_prefix}
ln -s libmozjs-38.so.${prefix%%-}	%{buildroot}%{_libdir}/libmozjs-38.so

%check
tests/jstests.py -d -s --no-progress ../../js/src/js/src/shell/js

%post -p /sbin/ldconfig

%postun -p /sbin/ldconfig

%files
%license ../../LICENSE
%doc ../../README
%{_libdir}/*.so.*

%files devel
%dir %{_libdir}/pkgconfig/
%{_libdir}/pkgconfig/*.pc
%{_includedir}/mozjs-%{major}
%{_libdir}/*.so

%changelog
* Wed Apr 6 2016 Marek Skalicky <mskalick@redhat.com> - 38.2.1-9
- Add missing symbolic link to library for devel subpackage

* Wed Apr 6 2016 Marek Skalicky <mskalick@redhat.com> - 38.2.1-8
- Fixed unprefixed rpm provides and requires (RHBZ#1321956)

* Thu Dec 10 2015 Marek Skalicky <mskalick@redhat.com> - 38.2.1-7
- Converted from Fedora 23 to support Software Collections

* Fri Dec 4 2015 Marek Skalicky <mskalick@redhat.com> - 38.2.1-6
- Make one function from vm/Runtime.cpp visible (needed by MongoDB 3.2)

* Thu Nov 26 2015 Dan Horák <dan[at]danny.cz> - 38.2.1-5
- fix build on s390 (rhbz#1219542)

* Wed Nov 25 2015 Marek Skalicky <mskalick@redhat.com> - 38.2.1-4
- Make two functions from CharacterEncoding.cpp visible (needed by MongoDB)

* Mon Oct 26 2015 Marcin Juszkiewicz <mjuszkiewicz@redhat.com> - 38.2.1-3
- Handle all Fedora 64-bit architectures.

* Tue Oct 13 2015 Marek Skalicky <mskalick@redhat.com> - 38.2.1-2
- Fixed inaccuracies from package review (paraller build, tests don't fail,...)

* Tue Oct 6 2015 Marek Skalicky <mskalick@redhat.com> - 38.2.1-1
- Initial mozjs38 spec (based on mozjs31)
