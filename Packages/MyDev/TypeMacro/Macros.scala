import scala.reflect.macros.Context
import language.experimental.macros

class C

object Macros {
  def impl(c: Context) = {
    import c.universe._
    HEREIdent(newTypeName("C"))
  }

  type Foo = macro impl
}