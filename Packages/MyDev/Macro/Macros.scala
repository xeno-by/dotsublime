import scala.reflect.macros.Context
import language.experimental.macros

object Macros {
  def impl(c: Context) = {
    import c.universe._
    HERE
  }

  def foo = macro impl
}