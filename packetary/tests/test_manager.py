"""
This file is part of fuel-mirror

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
   def test_resolve_with_master(self):
        master = Index()
        slave = Index()
        shared_package = package_generator(
            name="test1",
            requires=[
                objects.PackageRelation("test2"),
                objects.PackageRelation("test3"),
                objects.PackageRelation("test4")
            ]
        )
        master.add(shared_package)
        slave.add(shared_package)
        master.add(package_generator(name="test2", requires=None))
        test4 = package_generator(
            name="test4", requires=[objects.PackageRelation("test1")]
        )
        slave.add(test4)
        unresolved = master.get_unresolved()
        self.assertItemsEqual(
            ["test3", "test4"],
            [x.name for x in unresolved]
        )
        packages = slave.resolve(unresolved, master)
        self.assertItemsEqual([test4], packages)
        self.assertEqual(1, len(unresolved))
        self.assertEqual("test3", unresolved.pop().name)

    def test_resolve_without_master(self):
        index = Index()
        index.add(package_generator(name="test1", requires=None))
        index.add(package_generator(
            name="test2", requires=[objects.PackageRelation("test1")])
        )
        index.add(package_generator(
            name="test3",
            requires=[
                objects.PackageRelation("test1"),
                objects.PackageRelation("test4")
            ])
        )
        unresolved = set()
        unresolved.add(objects.PackageRelation("test3"))
        resolved = index.resolve(unresolved)
        self.assertItemsEqual(
            ["test3", "test1"],
            (x.name for x in resolved)
        )
        self.assertEqual(1, len(unresolved))
        self.assertEqual("test4", unresolved.pop().name)

    def test_get_unresolved(self):
        index = Index()
        index.add(package_generator(
            name="test1", requires=[objects.PackageRelation("test1")])
        )
        index.add(package_generator(
            name="test2", requires=[objects.PackageRelation("test1")])
        )
        package = package_generator(
            name="test3", requires=[objects.PackageRelation("test4")]
        )
        package.requires.append(objects.PackageRelation("test1"))
        index.add(package)
        unresolved = index.get_unresolved()
        self.assertEqual(2, len(unresolved))
        self.assertItemsEqual(
            ["test1", "test4"],
            [x.name for x in unresolved]
        )
