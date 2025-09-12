import React from 'react';
import MathRenderer from './MathRenderer';

const MathTestComponent = () => {
  const testContent = {
    plainMath: "Find the value of x where x² + 5x - 6 = 0",
    withSquareRoot: "The solution is √25 = 5",
    withDegrees: "In a right triangle, one angle is 30°",
    withLogarithm: "Calculate log₂(8) = 3",
    withSymbols: "We know that π ≈ 3.14 and θ = 45°",
    withLaTeX: "Using the quadratic formula: \\(x = \\frac{-b ± \\sqrt{b² - 4ac}}{2a}\\)",
    displayMath: "The area formula is: $$A = \\pi r^2$$",
    mixedContent: `Solution:
1. First, calculate x² + 2x = 8
2. Then find √16 = 4
3. Finally, note that 30° = π/6 radians
4. The answer is \\(x = 2\\)`
  };

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h2>Mathematical Rendering Test</h2>
      
      <div style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ddd', borderRadius: '8px' }}>
        <h3>Plain Math (Auto-Enhanced)</h3>
        <MathRenderer content={testContent.plainMath} />
      </div>
      
      <div style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ddd', borderRadius: '8px' }}>
        <h3>Square Root</h3>
        <MathRenderer content={testContent.withSquareRoot} />
      </div>
      
      <div style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ddd', borderRadius: '8px' }}>
        <h3>Degrees</h3>
        <MathRenderer content={testContent.withDegrees} />
      </div>
      
      <div style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ddd', borderRadius: '8px' }}>
        <h3>Logarithm</h3>
        <MathRenderer content={testContent.withLogarithm} />
      </div>
      
      <div style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ddd', borderRadius: '8px' }}>
        <h3>Symbols</h3>
        <MathRenderer content={testContent.withSymbols} />
      </div>
      
      <div style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ddd', borderRadius: '8px' }}>
        <h3>LaTeX Inline</h3>
        <MathRenderer content={testContent.withLaTeX} />
      </div>
      
      <div style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ddd', borderRadius: '8px' }}>
        <h3>Display Math</h3>
        <MathRenderer content={testContent.displayMath} />
      </div>
      
      <div style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ddd', borderRadius: '8px' }}>
        <h3>Mixed Content (With Line Breaks)</h3>
        <MathRenderer content={testContent.mixedContent} />
      </div>
    </div>
  );
};

export default MathTestComponent;