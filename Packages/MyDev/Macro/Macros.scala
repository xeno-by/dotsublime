import scala.reflect.macros.Context
import scala.language.experimental.macros

object Macros {
  def impl(c: Context) = {
    import c.universe._
    HERE
  }

  def foo = macro impl
}