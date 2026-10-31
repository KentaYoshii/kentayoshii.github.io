---
layout: page
title: Java
permalink: /dev/java/
description: Java tips and tricks.
---

<p class="breadcrumb"><a href="{{ '/dev/' | relative_url }}">Dev Notes</a> / Java</p>

<div class="java" markdown="1">

## Class 
### Builder design
If your class constructor becomes too big, it becomes hard to maintain. 
For such a scenario, builder pattern is good. The idea is, you create an inner _Builder_ class whose `build()` method will instantiate the outer class for you.

```java
public class Kenta {
    private final Integer a; // mandatory
    private final Integer b; // optional
    private final Integer c; // optional

    public static class KentaBuilder {
        Integer a; // mandatory
        Integer b = 0; // optional
        Integer c = 0; // optional
        
        public KentaBuilder(Integer a) {
            this.a = a;
        }

        public KentaBuilder setB(Integer b) {...}
        ...

        public Kenta build() { return new Kenta(this); }
    }

    private Kenta(KentaBuilder builder) {
        a = builder.a;
        b = builder.b;
        c = builder.c;
    }
}

```

With this, the caller can simply
- provide the parameters they are interested in
- chain the set... methods
- call build()

to get an immutable object.
### Singleton Pattern 
A few ways to achieve singleton pattern. 
1. Use a `public static final` field + make the constructor private
2. Use a _static factory method_ that returns a `private static final` field + make the constructor private
3. Use a single-element enum

```java
public enum Kenta {
    INSTANCE; // callers use Kenta.INSTANCE
}

```

### Dependency Injection
Static singleton / utility classes are inappropriate for classes whose behavior is parameterized by an underlying resource.

__Dependency Injection__
- Pass the resource into constructor when creating a new instance of the class.

This practice will greatly enhance the flexibility, reusability and testability of a class.

### try-with-resources
If your class manages resources (file handles, connections), there are two ways to do a graceful clean up.

```java
ClassWithResource rs = new ClassWithResource(...);
try {
    ...
} finally {
    rs.close(); // release
}
```

This first way is ok but:
- it can get easily crazy if you start nesting
- when nested, exceptions handling becomes odd
Prefer try-with-resources 

```java
try (ClassWithResource rs = new ClassWithResource(...)) {
    ...
}
```

For this to work, your class needs to implement `AutoCloseable` interface

### Memory Leak
Garbage Collection does a good job collecting / reclaiming objects with no references (unreachable). That said, it can NOT collect objects 
that have references to it. For example:
- Array Class that internally manages memory 
    - i.e., pop() needs to null out the cell 
- Cache Entry 
- ...

Important to anticipate problems like this when you are coding.

#### Finalizers and Cleaners

_Finalizers_ is an old java concept that has been since deprecated. 
- Mechanism to cleanup non-heap resources. 
- Heavy GC overhead + unpredictable execution on a finalizer thread 
- Safety Risks
_Cleaners_ is a safety net for cases when clients don't call your `close()` method.
- You define a Cleaner "job" and register it in constructor.


## Object
### equals() contract
- Define one if you want your class to have logical equality
- Contract
    - Reflexive
    - Symmetric
    - Transitive
    - Consistent
    - Non-nullity

### hashcode() contract
- MUST override when equals() is overridden
- If two objects are equal(), they must produce the SAME hashcode()
- If two objects are NOT equal(), it is NOT required they have DIFFERENT hashcode()
    - distinct results are good for performance

### toString() contract
- ALWAYS override!
    - Default is just `<class_name>@<hashcode_in_hex>`

### clone() contract
- The `Cloneable` interface
    - No interface methods
    - It drives the behavior of `Object`'s clone implementation.
- A class implementing `Cloneable` is expected to provide a `public` clone method.
- Why NOT to use it
    - The contract is not clear
    - NO constructor invocation
    - Throws checked exception 
    - No Polymorphism
- Usually copy constructor and / or static copy factory is better!
> For Java Array, clone() is still considered permitted

### Comparable interface
`Comparable` interface lets classes indicate _they have natural ordering_. 
- `compareTo()` is the sole interface method
`compareTo()` returns a negative number / zero / a positive number if `this` is less than / equal to / greater than the object passed in.
`Comparator` interface has a set of comparator construction methods (i.e. thenComparingInt) that you can use to fluently construct comparators. 

## Enums
An _enumerated type_ is a type whose legal values consist of a fixed set of constants.
- It is a full-fledged *class* that exports one instance for each enumeration constant via a `public static final` field.
    - It is instance-controlled. Clients cannot create an instance of an enumeration type.
- Enum provides compile-time safety. 
- You can have fields in Enum type. They should be `final`.
- If a different behavior is wanted for different enum type, you can declare an `abstract` method and have each enum create a _constant-specific class body_

```java
public enum Kenta {
    A { public void op... ;}, 
    B { public void op... ;}, 
    C { public void op... ;};

    public abstract void op(Object a, Object b);
}

```

- `switch` statements on enums are not a good choice for implementing constant-specific behavior on enums. 
    - They are good for _augmenting_ enum types with constant-specific behavior.

### Never use enum ordinals directly
Enum types are naturally associated with a single `int` value. This can be accessed via the `ordinal()` method.
Using this in your code will be a maintenance nightmare. A shift in position can break things. 
Instead simply create a _enum field_ and assign int to each type.

### EnumSet / EnumMap
EnumSet
- It is a bit vector whose underlying storage differs based on the number of Enum types. 
- If <= 64, it uses a `long`
- Performance is good and the methods are intuitive (`removeAll`, `retainAll`) as opposed to raw bit field.
EnumMap
- An implementation of Map that works with enum type keys. 
- Internally uses arrays where enum's _ordinal value_ is used as an index. 
- Because of this, performance is good. 

Try to use EnumMap / EnumSet where appropriate!

### Enum with interfaces
Enum types can implement arbitrary _interfaces_. You can then have your enum implement that interface and have other clients implement that interface etc.

## Annotations
A form of metadata that provides data about a program that is not part of the program itself. 
- Information for compiler
- Information for IDE tools
- Runtime processing 

_Annotation Type_ is a special kind of interface used to define metadata that can be attached to java code elements. 
- `@interface` keyword is used to declare one.

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.SOURCE)
public @interface Override {
}

```

- You can have annotation take in multiple values. Annotation type with NO value is called _marker annotation_.
Predefined annotations
- `@Override`
- `@Deprecated`
- `@SuppressWarnings`
- `@FunctionalInterface` (an interface type with EXACTLY one abstract method; used by the compiler as an enforcement. This is useful because _lambda_ can be used to instantiate an instance of it)
- `@SafeVarargs`

### Creating an annotation
When to create an annotation? 
- When I am attaching metadata to this program element so that x can validate, generate, configure, or execute something based on it.

How to create one? By using _meta-annotations_
- `@Retention`
    - How the marked annotation is stored (SOURCE/CLASS/RUNTIME).
- `@Documented`
    - Used by Javadoc tool
- `@Target`
    - Specify what kind of Java elements the annotation can be applied to
- `@Inherited`
    - Whether a annotation type can be inherited from the super class. 
- `@Repeatable`
    - Marked annotation can be applied more than once to the same declaration or type use. 
</div>
