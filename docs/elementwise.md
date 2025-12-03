# Element-wise Math Capability

The Element-wise Math capability provides high-performance, GPU-accelerated (where available) mathematical computations on numbers and arrays. It supports automatic broadcasting, allowing operations between scalars and arrays, or arrays of different compatible shapes.

## Tools

### `math_compute`

Performs a specific mathematical operation on input data.

**Features:**
- **Broadcasting:** Operations like `add([1, 2], 10)` result in `[11, 12]`.
- **Precision:** Supports `float32` (speed) and `float64` (accuracy).
- **Wide Range of Operations:** Arithmetic, Trigonometric, Exponential, Logical, etc.

**Supported Operations:**

| Category | Operations |
|----------|------------|
| **Arithmetic** | `add`, `subtract`, `multiply`, `divide`, `power`, `mod` |
| **Exponential/Log** | `exp`, `log` (natural), `log10`, `log2`, `sqrt`, `square` |
| **Trigonometric** | `sin`, `cos`, `tan`, `sinh`, `cosh`, `tanh` |
| **Rounding** | `floor`, `ceil`, `round` |
| **Comparison** | `greater`, `less`, `equal`, `not_equal`, `greater_equal`, `less_equal` |
| **Other** | `abs`, `negate`, `reciprocal`, `sign`, `sigmoid`, `relu`, `maximum`, `minimum` |

**Example Usage:**

*Calculate Square Root:*
```json
{
  "operation": "sqrt",
  "a": [4, 9, 16, 25]
}
```

*Element-wise Addition:*
```json
{
  "operation": "add",
  "a": [1, 2, 3],
  "b": [10, 20, 30]
}
```

### `math_list_operations`

Returns a complete list of all supported operations categorized by type (Unary vs Binary). Useful for dynamic discovery of capabilities.
