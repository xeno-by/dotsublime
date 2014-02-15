import scala.reflect.macros.whitebox._
import scala.language.experimental.macros

object Macros {
  def impl(c: Context) = {
    import c.universe._
    HERE
  }

  def foo: Any = macro impl
}