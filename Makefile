# Intel License for KCM (version January 2017)
#
# Copyright (c) 2017 Intel Corporation.
#
# Use.  You may use the software (the "Software"), without modification,
# provided the following conditions are met:
#
# * Neither the name of Intel nor the names of its suppliers may be used to
#   endorse or promote products derived from this Software without specific
#   prior written permission.
# * No reverse engineering, decompilation, or disassembly of this Software
#   is permitted.
#
# Limited patent license.  Intel grants you a world-wide, royalty-free,
# non-exclusive license under patents it now or hereafter owns or controls to
# make, have made, use, import, offer to sell and sell ("Utilize") this
# Software, but solely to the extent that any such patent is necessary to
# Utilize the Software alone. The patent license shall not apply to any
# combinations which include this software.  No hardware per se is licensed
# hereunder.
#
# Third party and other Intel programs.  "Third Party Programs" are the files
# listed in the "third-party-programs.txt" text file that is included with the
# Software and may include Intel programs under separate license terms. Third
# Party Programs, even if included with the distribution of the Materials, are
# governed by separate license terms and those license terms solely govern your
# use of those programs.
#
# DISCLAIMER.  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT ARE
# DISCLAIMED. THIS SOFTWARE IS NOT INTENDED NOR AUTHORIZED FOR USE IN SYSTEMS
# OR APPLICATIONS WHERE FAILURE OF THE SOFTWARE MAY CAUSE PERSONAL INJURY OR
# DEATH.
#
# LIMITATION OF LIABILITY. IN NO EVENT WILL INTEL BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. YOU AGREE TO
# INDEMNIFIY AND HOLD INTEL HARMLESS AGAINST ANY CLAIMS AND EXPENSES RESULTING
# FROM YOUR USE OR UNAUTHORIZED USE OF THE SOFTWARE.
#
# No support.  Intel may make changes to the Software, at any time without
# notice, and is not obligated to support, update or provide training for the
# Software.
#
# Termination. Intel may terminate your right to use the Software in the event
# of your breach of this Agreement and you fail to cure the breach within a
# reasonable period of time.
#
# Feedback.  Should you provide Intel with comments, modifications,
# corrections, enhancements or other input ("Feedback") related to the Software
# Intel will be free to use, disclose, reproduce, license or otherwise
# distribute or exploit the Feedback in its sole discretion without any
# obligations or restrictions of any kind, including without limitation,
# intellectual property rights or licensing obligations.
#
# Compliance with laws.  You agree to comply with all relevant laws and
# regulations governing your use, transfer, import or export (or prohibition
# thereof) of the Software.
#
# Governing law.  All disputes will be governed by the laws of the United
# States of America and the State of Delaware without reference to conflict of
# law principles and subject to the exclusive jurisdiction of the state or
# federal courts sitting in the State of Delaware, and each party agrees that
# it submits to the personal jurisdiction and venue of those courts and waives
# any objections. The United Nations Convention on Contracts for the
# International Sale of Goods (1980) is specifically excluded and will not
# apply to the Software.

.PHONY: docker docs

all: docker

version=v0.3.0

# TODO: This target should be changed, when e2e tests will be ready and test
# entrypoint will be defined.
jenkins: docker
	docker tag kcm:$(version) registry.dev.e2e/kcm:latest
	docker push registry.dev.e2e/kcm:latest

docker:
	docker build --no-cache -t kcm:$(version) .
	@echo ""
	@echo "To run the docker image, run command:"
	@echo "docker run -it kcm:$(version) ..."

# Output neatly formatted HTML docs to `docs/html`.
#
# This target uses `grip` (see https://github.com/joeyespo/grip).
#
# The files are passed securely to the GitHub rendering API.
# GitHub imposes a limit of 60 unauthorized requests per hour.
# To authenticate, create a personal access token and add it to a file
# named `~/grip/settings.py` as described in the project README.
docs:
	pip install grip
	mkdir -p docs/html/docs
	cp -R docs/images docs/html/docs/
	grip README.md --export docs/html/index.html --title="KCM"
	grip docs/build.md --export docs/html/docs/build.html --title="Building kcm"
	grip docs/cli.md --export docs/html/docs/cli.html --title="Using the kcm command-line tool"
	grip docs/config.md --export docs/html/docs/config.html --title="The kcm configuration directory"
	grip docs/operator.md --export docs/html/docs/operator.html --title="kcm operator manual"
	grip docs/user.md --export docs/html/docs/user.html --title="kcm user manual"
	sed -i"" "s/\.md/\.html/g" docs/html/index.html
	sed -i"" "s/\.md/\.html/g" docs/html/docs/build.html
	sed -i"" "s/\.md/\.html/g" docs/html/docs/cli.html
	sed -i"" "s/\.md/\.html/g" docs/html/docs/config.html
	sed -i"" "s/\.md/\.html/g" docs/html/docs/operator.html
	sed -i"" "s/\.md/\.html/g" docs/html/docs/user.html
