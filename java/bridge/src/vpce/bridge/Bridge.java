package vpce.bridge;

import com.vp.plugin.VPPlugin;
import com.vp.plugin.VPPluginCommandLineSupport;
import com.vp.plugin.VPPluginInfo;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.nio.charset.Charset;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Enumeration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.jar.JarEntry;
import java.util.jar.JarFile;

/**
 * Generic reflective bridge into the Visual Paradigm Open API.
 *
 * The command runs headless inside a VP process:
 *
 *   java ... com.vp.cmd.Plugin -project X -pluginid com.vpce.bridge -pluginargs <base64 script>
 *
 * The script is UTF-8 text, one statement per line:
 *
 *   // comment
 *   @search IModelElement            -- list classes on the classpath matching a regex
 *   @introspect com.vp.plugin.IDiagram
 *   $am = ApplicationManager.instance()
 *   $p  = $am.getProjectManager().getProject()
 *   $p.getModel().getName()
 *
 * Results come back as one line per statement and the whole response is printed
 * as "VPCE_RESP <base64>". Nothing but that marker is written to stdout.
 */
public class Bridge implements VPPlugin, VPPluginCommandLineSupport {

    private static final Charset UTF8 = Charset.forName("UTF-8");
    private static final String MARKER = "VPCE_RESP ";

    private final Map<String, Object> vars = new LinkedHashMap<String, Object>();

    // ---------------------------------------------------------------- plugin

    public void loaded(VPPluginInfo info) {
    }

    public void unloaded() {
    }

    public void invoke(String[] args) {
        String script;
        try {
            String blob = args.length == 0 ? "" : String.join("", args);
            script = new String(Base64.getDecoder().decode(blob), UTF8);
        } catch (Throwable t) {
            emit("# decode error: " + t);
            return;
        }
        emit(run(script));
    }

    private static void emit(String body) {
        String b64 = Base64.getEncoder().encodeToString(body.getBytes(UTF8));
        System.out.println(MARKER + b64);
        System.out.flush();
    }

    // ---------------------------------------------------------------- script

    private String run(String script) {
        StringBuilder out = new StringBuilder();
        String[] lines = script.split("\\r?\\n");
        int n = 0;
        for (String raw : lines) {
            String line = raw.trim();
            if (line.isEmpty() || line.startsWith("//") || line.startsWith("#")) {
                continue;
            }
            n++;
            try {
                if (line.startsWith("@search")) {
                    out.append(handleSearch(line.substring(7).trim())).append('\n');
                } else if (line.startsWith("@introspect")) {
                    out.append(handleIntrospect(line.substring(11).trim())).append('\n');
                } else {
                    out.append(handleStatement(line, n)).append('\n');
                }
            } catch (Throwable t) {
                Throwable root = rootCause(t);
                out.append("error#").append(n).append(' ')
                   .append(root.getClass().getName()).append(": ")
                   .append(String.valueOf(root.getMessage())).append('\n');
            }
        }
        return out.toString();
    }

    private String handleStatement(String line, int n) throws Exception {
        String target = line;
        String assign = null;
        int eq = line.indexOf('=');
        if (eq > 0) {
            String left = line.substring(0, eq).trim();
            if (left.matches("\\$[A-Za-z_]\\w*")) {
                assign = left.substring(1);
                target = line.substring(eq + 1).trim();
            }
        }
        Object value = eval(target);
        if (assign != null) {
            vars.put(assign, value);
            return "$" + assign + " = " + describe(value);
        }
        return "r" + n + " = " + describe(value);
    }

    // --------------------------------------------------------------- search

    private String handleSearch(String pattern) {
        List<String> hits = scan(pattern);
        StringBuilder sb = new StringBuilder("search ").append(pattern)
                .append(" -> ").append(hits.size()).append('\n');
        for (int i = 0; i < hits.size() && i < 400; i++) {
            sb.append("  ").append(hits.get(i)).append('\n');
        }
        if (hits.size() > 400) {
            sb.append("  ... truncated\n");
        }
        return sb.toString().trim();
    }

    /** Class names under com.vp.plugin that contain {@code needle} (case-insensitive). */
    private static List<String> scan(String needle) {
        String pat = needle.toLowerCase();
        java.util.Set<String> hits = new java.util.LinkedHashSet<String>();
        String cp = System.getProperty("java.class.path", "");
        for (String entry : cp.split(File.pathSeparator)) {
            if (!entry.toLowerCase().endsWith(".jar")) {
                continue;
            }
            try (JarFile jar = new JarFile(entry)) {
                Enumeration<JarEntry> en = jar.entries();
                while (en.hasMoreElements()) {
                    String name = en.nextElement().getName();
                    if (!name.endsWith(".class") || name.indexOf('$') >= 0) {
                        continue;
                    }
                    if (!name.startsWith("com/vp/plugin/")) {
                        continue;
                    }
                    String cls = name.substring(0, name.length() - 6).replace('/', '.');
                    if (cls.toLowerCase().contains(pat)) {
                        hits.add(cls);
                    }
                }
            } catch (Throwable ignored) {
            }
        }
        List<String> sorted = new ArrayList<String>(hits);
        java.util.Collections.sort(sorted);
        return sorted;
    }

    private String handleIntrospect(String className) throws Exception {
        Class<?> c = resolveClass(className);
        StringBuilder sb = new StringBuilder("class ").append(c.getName());
        Class<?> sup = c.getSuperclass();
        if (sup != null && sup != Object.class) {
            sb.append(" extends ").append(sup.getName());
        }
        Class<?>[] ifs = c.getInterfaces();
        if (ifs.length > 0) {
            sb.append(" implements ");
            for (int i = 0; i < ifs.length; i++) {
                sb.append(i > 0 ? "," : "").append(ifs[i].getSimpleName());
            }
        }
        sb.append('\n');
        Field[] fs = c.getFields();
        java.util.Arrays.sort(fs, new java.util.Comparator<Field>() {
            public int compare(Field a, Field b) {
                return a.getName().compareTo(b.getName());
            }
        });
        for (Field f : fs) {
            if (Modifier.isStatic(f.getModifiers())) {
                Object v = null;
                try {
                    v = f.get(null);
                } catch (Throwable ignored) {
                }
                sb.append("  .").append(f.getName()).append(" : ").append(simple(f.getType()))
                  .append(" = ").append(v).append('\n');
            }
        }
        Method[] ms = c.getMethods();
        java.util.Arrays.sort(ms, new java.util.Comparator<Method>() {
            public int compare(Method a, Method b) {
                return a.getName().compareTo(b.getName());
            }
        });
        for (Method m : ms) {
            if (m.getDeclaringClass() == Object.class) {
                continue;
            }
            sb.append("  ").append(m.getName()).append('(');
            Class<?>[] ps = m.getParameterTypes();
            for (int i = 0; i < ps.length; i++) {
                sb.append(i > 0 ? ", " : "").append(simple(ps[i]));
            }
            sb.append(") : ").append(simple(m.getReturnType())).append('\n');
        }
        return sb.toString().trim();
    }

    /** Unwrap reflection wrappers so callers see the real exception. */
    private static Throwable rootCause(Throwable t) {
        Throwable cur = t;
        int guard = 8;
        while (guard-- > 0) {
            Throwable next = cur.getCause();
            if (next == null || next == cur) {
                break;
            }
            cur = next;
        }
        return cur;
    }

    private static String simple(Class<?> c) {        if (c.isArray()) {
            return simple(c.getComponentType()) + "[]";
        }
        String n = c.getName();
        return n.startsWith("java.lang.") ? n.substring(10) : n;
    }

    // ----------------------------------------------------------- evaluation

    private Object eval(String expr) throws Exception {
        expr = expr.trim();
        List<String> segs = split(expr, '.');
        String head = segs.get(0).trim();
        Object cur;
        if (head.startsWith("$")) {
            String name = head.substring(1);
            if (!vars.containsKey(name)) {
                throw new IllegalArgumentException("unknown variable: " + head);
            }
            cur = vars.get(name);
        } else if (head.endsWith(")")) {
            cur = callStatic(null, head);
        } else if (head.indexOf('(') < 0) {
            // bare identifier: class reference, static field or string
            try {
                cur = resolveClass(head);
            } catch (Throwable t) {
                cur = head;
            }
        } else {
            cur = callStatic(null, head);
        }
        for (int i = 1; i < segs.size(); i++) {
            cur = step(cur, segs.get(i));
        }
        return cur;
    }

    private Object step(Object target, String seg) throws Exception {
        seg = seg.trim();
        if (seg.isEmpty()) {
            return target;
        }
        if (target != null && target.getClass().isArray()) {
            int len = java.lang.reflect.Array.getLength(target);
            if ("length".equals(seg)) {
                return Integer.valueOf(len);
            }
            if (seg.startsWith("get(") && seg.endsWith(")")) {
                int idx = Integer.parseInt(seg.substring(4, seg.length() - 1).trim());
                return java.lang.reflect.Array.get(target, idx);
            }
        }
        if (target instanceof Class) {
            Class<?> c = (Class<?>) target;
            if (seg.endsWith(")")) {
                return callStatic(c, seg);
            }
            try {
                Field f = c.getField(seg);
                return f.get(null);
            } catch (NoSuchFieldException e) {
                Method m = find(c, seg, new Object[0]);
                return m.invoke(null, new Object[0]);
            }
        }
        if (seg.endsWith(")")) {
            return callInstance(target, seg);
        }
        Method m = find(target.getClass(), seg, new Object[0]);
        return m.invoke(target, new Object[0]);
    }

    private Object callStatic(Class<?> owner, String call) throws Exception {
        int p = call.indexOf('(');
        String name = call.substring(0, p).trim();
        List<String> argSrc = splitArgs(call.substring(p + 1, call.lastIndexOf(')')));
        if (owner == null) {
            int dot = name.lastIndexOf('.');
            if (dot < 0) {
                throw new IllegalArgumentException("static call needs a class: " + call);
            }
            owner = resolveClass(name.substring(0, dot));
            name = name.substring(dot + 1);
        }
        Object[] args = new Object[argSrc.size()];
        for (int i = 0; i < args.length; i++) {
            args[i] = argValue(argSrc.get(i));
        }
        Method m = find(owner, name, args);
        return m.invoke(null, coerceAll(m, args));
    }

    private Object callInstance(Object target, String call) throws Exception {
        int p = call.indexOf('(');
        String name = call.substring(0, p).trim();
        List<String> argSrc = splitArgs(call.substring(p + 1, call.lastIndexOf(')')));
        Object[] args = new Object[argSrc.size()];
        for (int i = 0; i < args.length; i++) {
            args[i] = argValue(argSrc.get(i));
        }
        Method m = find(target.getClass(), name, args);
        return m.invoke(target, coerceAll(m, args));
    }

    private Object argValue(String src) throws Exception {
        src = src.trim();
        if (src.isEmpty()) {
            return "";
        }
        if (src.startsWith("$")) {
            return vars.get(src.substring(1));
        }
        if (src.startsWith("\"") && src.endsWith("\"") && src.length() >= 2) {
            return src.substring(1, src.length() - 1).replace("\\\"", "\"").replace("\\n", "\n");
        }
        if ("true".equals(src)) {
            return Boolean.TRUE;
        }
        if ("false".equals(src)) {
            return Boolean.FALSE;
        }
        if ("null".equals(src)) {
            return null;
        }
        if (src.matches("-?\\d+")) {
            return Long.valueOf(src);
        }
        if (src.matches("-?\\d*\\.\\d+")) {
            return Double.valueOf(src);
        }
        // STATIC_FIELD reference, e.g. com.vp.plugin.diagram.DiagramTypeConstants.UML_CLASS_DIAGRAM
        if (src.matches("[A-Za-z_][\\w.]*\\.[A-Z][A-Z0-9_]*")) {
            int dot = src.lastIndexOf('.');
            Class<?> owner = resolveClass(src.substring(0, dot));
            return owner.getField(src.substring(dot + 1)).get(null);
        }
        return src;
    }

    private static Method find(Class<?> owner, String name, Object[] args) throws NoSuchMethodException {
        Method best = null;
        int bestScore = Integer.MIN_VALUE;
        for (Method m : candidates(owner)) {
            if (!m.getName().equals(name) || m.getParameterTypes().length != args.length) {
                continue;
            }
            int score = 0;
            Class<?>[] ps = m.getParameterTypes();
            for (int i = 0; i < ps.length; i++) {
                score += score(ps[i], args[i]);
            }
            if (score > bestScore) {
                bestScore = score;
                best = m;
            }
        }
        if (best == null) {
            throw new NoSuchMethodException(owner.getName() + "." + name + "/" + args.length);
        }
        try {
            best.setAccessible(true);
        } catch (Throwable ignored) {
        }
        return best;
    }

    /**
     * All public methods visible on an object: the runtime class is often a
     * package-private implementation, so interface methods have to be
     * collected explicitly or the reflection call fails with
     * IllegalAccessException despite the method existing.
     */
    private static List<Method> candidates(Class<?> owner) {
        List<Method> out = new ArrayList<Method>();
        java.util.Set<String> seen = new java.util.HashSet<String>();
        collect(owner, out, seen, 0);
        return out;
    }

    private static void collect(Class<?> c, List<Method> out, java.util.Set<String> seen, int depth) {
        if (c == null || depth > 6) {
            return;
        }
        for (Method m : c.getMethods()) {
            String key = m.getName() + "/" + m.getParameterTypes().length + "/"
                    + java.util.Arrays.toString(m.getParameterTypes());
            if (seen.add(key)) {
                out.add(m);
            }
        }
        for (Class<?> i : c.getInterfaces()) {
            collect(i, out, seen, depth + 1);
        }
        collect(c.getSuperclass(), out, seen, depth + 1);
    }

    private static int score(Class<?> p, Object a) {
        if (a == null) {
            return p.isPrimitive() ? -5 : 1;
        }
        if (p.isInstance(a)) {
            return 10;
        }
        if (p == int.class && a instanceof Number) return 8;
        if (p == long.class && a instanceof Number) return 8;
        if (p == double.class && a instanceof Number) return 7;
        if (p == boolean.class && a instanceof Boolean) return 8;
        if (p == String.class) return 3;
        if (p == Object.class) return 2;
        return -1;
    }

    private static Object[] coerceAll(Method m, Object[] args) {
        Class<?>[] ps = m.getParameterTypes();
        Object[] out = new Object[args.length];
        for (int i = 0; i < args.length; i++) {
            out[i] = coerce(ps[i], args[i]);
        }
        return out;
    }

    private static Object coerce(Class<?> p, Object a) {
        if (a == null) {
            return null;
        }
        if (p.isInstance(a)) {
            return a;
        }
        String s = String.valueOf(a);
        if (p == String.class) return s;
        if (p == int.class || p == Integer.class) return Integer.valueOf((int) toLong(s));
        if (p == long.class || p == Long.class) return Long.valueOf(toLong(s));
        if (p == short.class || p == Short.class) return Short.valueOf((short) toLong(s));
        if (p == byte.class || p == Byte.class) return Byte.valueOf((byte) toLong(s));
        if (p == double.class || p == Double.class) return Double.valueOf(Double.parseDouble(s));
        if (p == float.class || p == Float.class) return Float.valueOf(Float.parseFloat(s));
        if (p == boolean.class || p == Boolean.class) return Boolean.valueOf(s);
        if (p == char.class || p == Character.class) return Character.valueOf(s.isEmpty() ? ' ' : s.charAt(0));
        return a;
    }

    private static long toLong(String s) {
        String t = s.trim();
        if (t.endsWith(".0")) {
            t = t.substring(0, t.length() - 2);
        }
        return Long.parseLong(t);
    }

    // ------------------------------------------------------------- describe

    private static String describe(Object v) {
        if (v == null) {
            return "null";
        }
        if (v instanceof String || v instanceof Number || v instanceof Boolean) {
            return v.getClass().getSimpleName() + " " + v;
        }
        if (v instanceof Class) {
            return "Class " + ((Class<?>) v).getName();
        }
        String fqn = v.getClass().getName();
        StringBuilder sb = new StringBuilder(v.getClass().getSimpleName());
        String extra = probe(v, "getId");
        if (extra != null) {
            sb.append("(id=").append(extra);
            String name = probe(v, "getName");
            if (name != null) {
                sb.append(", name=").append(name);
            }
            sb.append(", class=").append(fqn).append(')');
            return sb.toString();
        }
        String name = probe(v, "getName");
        if (name != null) {
            sb.append("(name=").append(name).append(", class=").append(fqn).append(')');
            return sb.toString();
        }
        String s = String.valueOf(v);
        if (s.length() > 300) {
            s = s.substring(0, 300) + "...";
        }
        return sb.append("[class=").append(fqn).append("] ").append(s).toString();
    }

    private static String probe(Object v, String getter) {
        try {
            Method m = v.getClass().getMethod(getter);
            Object r = m.invoke(v);
            return r == null ? null : String.valueOf(r);
        } catch (Throwable t) {
            return null;
        }
    }

    // ---------------------------------------------------------------- utils

    private static Class<?> resolveClass(String name) throws ClassNotFoundException {
        String n = name.trim();
        String[] prefixes = {"", "com.vp.plugin.", "com.vp.plugin.model.", "com.vp.plugin.diagram.",
                "com.vp.plugin.diagram.shape.", "com.vp.plugin.view.", "com.vp.plugin.action."};
        for (String p : prefixes) {
            try {
                return Class.forName(p + n, true, Bridge.class.getClassLoader());
            } catch (Throwable ignored) {
            }
        }
        // full static path that ends in a class name (a.b.C.D -> try prefix)
        int dot = n.lastIndexOf('.');
        while (dot > 0) {
            String prefix = n.substring(0, dot);
            for (String p : new String[]{"", "com.vp.plugin.", "com.vp.plugin.model.", "com.vp.plugin.diagram."}) {
                try {
                    return Class.forName(p + prefix, true, Bridge.class.getClassLoader());
                } catch (Throwable ignored) {
                }
            }
            dot = n.lastIndexOf('.', dot - 1);
        }
        // last resort: simple-name lookup over the Open API surface
        if (n.indexOf('.') < 0) {
            String fqn = simpleIndex().get(n);
            if (fqn != null) {
                return Class.forName(fqn, true, Bridge.class.getClassLoader());
            }
        }
        throw new ClassNotFoundException(name);
    }

    private static Map<String, String> simpleIndex;

    private static synchronized Map<String, String> simpleIndex() {
        if (simpleIndex != null) {
            return simpleIndex;
        }
        Map<String, String> idx = new LinkedHashMap<String, String>();
        for (String cls : scan("")) {
            String simple = cls.substring(cls.lastIndexOf('.') + 1);
            if (!idx.containsKey(simple)) {
                idx.put(simple, cls);
            }
        }
        simpleIndex = idx;
        return idx;
    }

    /** Split on a separator, ignoring separators inside quotes or parentheses. */
    private static List<String> split(String s, char sep) {
        List<String> out = new ArrayList<String>();
        int depth = 0;
        boolean quote = false;
        StringBuilder cur = new StringBuilder();
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '"') {
                quote = !quote;
            }
            if (!quote) {
                if (c == '(') depth++;
                if (c == ')') depth--;
                if (c == sep && depth == 0) {
                    out.add(cur.toString());
                    cur.setLength(0);
                    continue;
                }
            }
            cur.append(c);
        }
        out.add(cur.toString());
        return out;
    }

    private static List<String> splitArgs(String s) {
        List<String> out = new ArrayList<String>();
        if (s.trim().isEmpty()) {
            return out;
        }
        for (String part : split(s, ',')) {
            out.add(part.trim());
        }
        return out;
    }
}
