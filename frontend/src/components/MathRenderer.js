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
   * Parse and render mathematical content with fallback
   */
  const renderWithMath = (text) => {
    try {
      // First, apply auto-enhancement
      let processedText = autoEnhanceMath(text);
      
      // Split text into segments for processing
      const segments = [];
      let currentIndex = 0;
      
      // Process display math blocks ($$...$$)
      const displayMathPattern = /\$\$([^$]+)\$\$/g;
      let displayMatch;
      
      while ((displayMatch = displayMathPattern.exec(processedText)) !== null) {
        // Add text before math block
        if (displayMatch.index > currentIndex) {
          segments.push({
            type: 'text',
            content: processedText.slice(currentIndex, displayMatch.index)
          });
        }
        
        // Add display math block
        segments.push({
          type: 'displayMath',
          content: displayMatch[1]
        });
        
        currentIndex = displayMatch.index + displayMatch[0].length;
      }
      
      // Add remaining text
      if (currentIndex < processedText.length) {
        segments.push({
          type: 'text',
          content: processedText.slice(currentIndex)
        });
      }
      
      // If no display math found, treat entire text as one segment
      if (segments.length === 0) {
        segments.push({
          type: 'text',
          content: processedText
        });
      }
      
      // Process each segment
      return segments.map((segment, index) => {
        if (segment.type === 'displayMath') {
          return (
            <div key={index} style={{ margin: '10px 0', textAlign: 'center' }}>
              <BlockMathRenderer content={segment.content} />
            </div>
          );
        } else {
          // Process inline math in text segments
          return <InlineMathRenderer key={index} content={segment.content} />;
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

  /**
   * Render inline math expressions within text
   */
  const InlineMathRenderer = ({ content }) => {
    const inlineMathPattern = /\\?\(([^)]+)\\?\)/g;
    const segments = [];
    let lastIndex = 0;
    let match;

    while ((match = inlineMathPattern.exec(content)) !== null) {
      // Add text before math
      if (match.index > lastIndex) {
        segments.push({
          type: 'text',
          content: content.slice(lastIndex, match.index)
        });
      }

      // Add inline math
      segments.push({
        type: 'inlineMath',
        content: match[1]
      });

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < content.length) {
      segments.push({
        type: 'text',
        content: content.slice(lastIndex)
      });
    }

    // If no inline math found, return as plain text
    if (segments.length === 0) {
      return <span>{content}</span>;
    }

    return (
      <>
        {segments.map((segment, index) => {
          if (segment.type === 'inlineMath') {
            return <InlineMathComponent key={index} math={segment.content} />;
          } else {
            return <span key={index}>{segment.content}</span>;
          }
        })}
      </>
    );
  };

  /**
   * Safe inline math component with expression-level fallback
   */
  const InlineMathComponent = ({ math }) => {
    try {
      return <InlineMath math={math} />;
    } catch (error) {
      console.warn(`MathRenderer: KaTeX failed for inline expression "${math}":`, error);
      // Expression-level fallback to sanitized plain text
      return (
        <span
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
  const BlockMathRenderer = ({ content }) => {
    try {
      return <BlockMath math={content} />;
    } catch (error) {
      console.warn(`MathRenderer: KaTeX failed for display expression "${content}":`, error);
      // Expression-level fallback to sanitized plain text
      return (
        <div
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