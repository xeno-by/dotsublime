import scala.reflect.runtime.universe._
import scala.reflect.runtime.{currentMirror => cm}
import scala.tools.reflect.ToolBox
import scala.tools.reflect.Eval
import Macros._

object Test extends App {
  class D extends Foo
}