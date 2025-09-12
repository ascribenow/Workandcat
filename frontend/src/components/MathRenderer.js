/**
 * MathRenderer Component - Enhanced Mathematical Display
 * 
 * Render pipeline order: LaTeX-delimited > safe auto-enhance > plain text
 * Fallback: expression-level with telemetry
 * Performance: detect-then-render; lazy-load KaTeX bundle when math is present
 */

import React from 'react';
import { InlineMath, BlockMath } from 'react-katex';
import DOMPurify from 'dompurify';
import 'katex/dist/katex.min.css';

const MathRenderer = ({ content, className = '', style = {} }) => {
  // Early return for empty content
  if (!content) return null;

  /**
   * Detect if content contains mathematical expressions
   * Triggers: LaTeX delimiters, Unicode math symbols, subscript patterns
   */
  const hasMathContent = (text) => {
    const mathIndicators = [
      /\\[\(\)]/,           // LaTeX delimiters \( \)
      /\$\$/,               // Display math $$
      /[²³⁴⁵⁶⁷⁸⁹⁰]/,      // Superscript numbers
      /[₀₁₂₃₄₅₆₇₈₉]/,      // Subscript numbers
      /[√∫∑∏∆∇∂]/,         // Math symbols
      /[≤≥≠±×÷]/,          // Comparison/operation symbols
      /[πθαβγλμσΩ]/,       // Greek letters
      /°/,                 // Degree symbol
      /log[₀₁₂₃₄₅₆₇₈₉]/,   // Logarithm with subscript
    ];
    
    return mathIndicators.some(pattern => pattern.test(text));
  };

  /**
   * Safe auto-enhancement: Convert common Unicode math symbols to LaTeX
   */
  const autoEnhanceMath = (text) => {
    let enhanced = text;
    
    // Superscript conversions
    enhanced = enhanced.replace(/([a-zA-Z0-9])²/g, '\\($1^{2}\\)');
    enhanced = enhanced.replace(/([a-zA-Z0-9])³/g, '\\($1^{3}\\)');
    enhanced = enhanced.replace(/([a-zA-Z0-9])⁴/g, '\\($1^{4}\\)');
    enhanced = enhanced.replace(/([a-zA-Z0-9])⁵/g, '\\($1^{5}\\)');
    enhanced = enhanced.replace(/([a-zA-Z0-9])⁶/g, '\\($1^{6}\\)');
    enhanced = enhanced.replace(/([a-zA-Z0-9])⁷/g, '\\($1^{7}\\)');
    enhanced = enhanced.replace(/([a-zA-Z0-9])⁸/g, '\\($1^{8}\\)');
    enhanced = enhanced.replace(/([a-zA-Z0-9])⁹/g, '\\($1^{9}\\)');
    
    // Square root
    enhanced = enhanced.replace(/√(\d+)/g, '\\(\\sqrt{$1}\\)');
    enhanced = enhanced.replace(/√\(([^)]+)\)/g, '\\(\\sqrt{$1}\\)');
    
    // Degree symbol
    enhanced = enhanced.replace(/(\d+)°/g, '\\($1^\\circ\\)');
    
    // Logarithm subscripts
    enhanced = enhanced.replace(/log₂/g, '\\(\\log_{2}\\)');
    enhanced = enhanced.replace(/log₃/g, '\\(\\log_{3}\\)');
    enhanced = enhanced.replace(/log₁₀/g, '\\(\\log_{10}\\)');
    
    // Common mathematical symbols (pass through, already LaTeX compatible)
    const symbolMap = {
      '≤': '\\(\\leq\\)',
      '≥': '\\(\\geq\\)',
      '≠': '\\(\\neq\\)',
      '±': '\\(\\pm\\)',
      '×': '\\(\\times\\)',
      '÷': '\\(\\div\\)',
      'π': '\\(\\pi\\)',
      'θ': '\\(\\theta\\)',
      'α': '\\(\\alpha\\)',
      'β': '\\(\\beta\\)',
      'γ': '\\(\\gamma\\)',
      'λ': '\\(\\lambda\\)',
      'μ': '\\(\\mu\\)',
      'σ': '\\(\\sigma\\)',
      'Ω': '\\(\\Omega\\)'
    };
    
    Object.entries(symbolMap).forEach(([symbol, latex]) => {
      enhanced = enhanced.replace(new RegExp(symbol, 'g'), latex);
    });
    
    return enhanced;
  };

  /**
   * Safe inline math component with expression-level fallback
   */
  const renderInlineMath = (math) => {
    try {
      return <InlineMath key={`inline-${math}`} math={math} />;
    } catch (error) {
      console.warn(`MathRenderer: KaTeX failed for inline expression "${math}":`, error);
      // Expression-level fallback to sanitized plain text
      return (
        <span
          key={`fallback-${math}`}
          style={{ color: '#666', fontStyle: 'italic' }}
          title="Mathematical expression (display limited)"
        >
          {DOMPurify.sanitize(math, { ALLOWED_TAGS: [] })}
        </span>
      );
    }
  };

  /**
   * Safe block math component with expression-level fallback
   */
  const renderBlockMath = (content) => {
    try {
      return <BlockMath key={`block-${content}`} math={content} />;
    } catch (error) {
      console.warn(`MathRenderer: KaTeX failed for display expression "${content}":`, error);
      // Expression-level fallback to sanitized plain text
      return (
        <div
          key={`block-fallback-${content}`}
          style={{ 
            color: '#666', 
            fontStyle: 'italic',
            textAlign: 'center',
            padding: '10px',
            backgroundColor: '#f9f9f9',
            border: '1px dashed #ccc',
            borderRadius: '4px'
          }}
          title="Mathematical expression (display limited)"
        >
          {DOMPurify.sanitize(content, { ALLOWED_TAGS: [] })}
        </div>
      );
    }
  };

  /**
   * Parse and render mathematical content with fallback
   */
  const renderWithMath = (text) => {
    try {
      // First, apply auto-enhancement
      let processedText = autoEnhanceMath(text);
      
      // Process display math blocks ($$...$$) first
      const displayMathPattern = /\$\$([^$]+)\$\$/g;
      const displayMathSegments = [];
      let lastIndex = 0;
      let match;

      while ((match = displayMathPattern.exec(processedText)) !== null) {
        // Add text before display math
        if (match.index > lastIndex) {
          const textContent = processedText.slice(lastIndex, match.index);
          displayMathSegments.push({ type: 'text', content: textContent });
        }
        
        // Add display math
        displayMathSegments.push({ type: 'displayMath', content: match[1] });
        lastIndex = match.index + match[0].length;
      }

      // Add remaining text
      if (lastIndex < processedText.length) {
        displayMathSegments.push({ type: 'text', content: processedText.slice(lastIndex) });
      }

      // If no display math, treat as single text segment
      if (displayMathSegments.length === 0) {
        displayMathSegments.push({ type: 'text', content: processedText });
      }

      // Process each segment
      return displayMathSegments.map((segment, segIndex) => {
        if (segment.type === 'displayMath') {
          return (
            <div key={segIndex} style={{ margin: '10px 0', textAlign: 'center' }}>
              {renderBlockMath(segment.content)}
            </div>
          );
        } else {
          // Process inline math in text segments
          const inlinePattern = /\\?\(([^)]+)\\?\)/g;
          const inlineSegments = [];
          let inlineLastIndex = 0;
          let inlineMatch;

          while ((inlineMatch = inlinePattern.exec(segment.content)) !== null) {
            // Add text before inline math
            if (inlineMatch.index > inlineLastIndex) {
              inlineSegments.push({
                type: 'text',
                content: segment.content.slice(inlineLastIndex, inlineMatch.index)
              });
            }

            // Add inline math
            inlineSegments.push({
              type: 'inlineMath',
              content: inlineMatch[1]
            });

            inlineLastIndex = inlineMatch.index + inlineMatch[0].length;
          }

          // Add remaining text
          if (inlineLastIndex < segment.content.length) {
            inlineSegments.push({
              type: 'text',
              content: segment.content.slice(inlineLastIndex)
            });
          }

          // If no inline math, return as plain text
          if (inlineSegments.length === 0) {
            return <span key={segIndex}>{segment.content}</span>;
          }

          return (
            <span key={segIndex}>
              {inlineSegments.map((inlineSeg, inlineIndex) => {
                if (inlineSeg.type === 'inlineMath') {
                  return renderInlineMath(inlineSeg.content);
                } else {
                  return <span key={inlineIndex}>{inlineSeg.content}</span>;
                }
              })}
            </span>
          );
        }
      });
      
    } catch (error) {
      console.warn('MathRenderer: Error processing mathematical content:', error);
      // Fallback to sanitized plain text
      return (
        <span
          dangerouslySetInnerHTML={{
            __html: DOMPurify.sanitize(text, { ALLOWED_TAGS: [] })
          }}
        />
      );
    }
  };

  // Performance optimization: Only process if math content detected
  if (!hasMathContent(content)) {
    // Fast path: plain text rendering with preserved formatting
    return (
      <div 
        className={className} 
        style={{ 
          whiteSpace: 'pre-wrap',
          ...style 
        }}
      >
        {content}
      </div>
    );
  }

  // Math content detected: process through math renderer
  return (
    <div 
      className={className} 
      style={{ 
        whiteSpace: 'pre-wrap',
        ...style 
      }}
    >
      {renderWithMath(content)}
    </div>
  );
};

export default MathRenderer;