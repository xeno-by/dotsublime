import scala.reflect.macros.WhiteboxContext
import scala.language.experimental.macros

object Macros {
  def impl(c: WhiteboxContext) = {
    import c.universe._
    HERE
  }

  def foo: Any = macro impl
}