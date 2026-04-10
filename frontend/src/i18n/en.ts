// English translations
export const en = {
  // Navigation
  nav: {
    home: "Home",
    papers: "Papers",
    concepts: "Concepts",
    citations: "Citations",
  },

  // Home page
  home: {
    title: "Knowledge Landscape",
    subtitle: '"The universe of ideas, mapped and connected"',
    stats: {
      papers: "Papers",
      concepts: "Concepts",
      relations: "Relations",
      roots: "Roots",
    },
    actions: {
      uploadPapers: "Upload Papers",
      uploadDesc: "Import PDFs and extract knowledge concepts",
      exploreConcepts: "Explore Concepts",
      exploreDesc: "Navigate the hierarchical knowledge tree",
    },
    config: "Configuration",
    llmProvider: "LLM Provider",
    semanticScholar: "Semantic Scholar",
    processingStatus: "Processing Status",
    notConfigured: "Not configured",
    enabled: "Enabled",
    disabled: "Disabled",
  },

  // Papers page
  papers: {
    title: "Paper Library",
    subtitle: "Manage and process your academic papers",
    refresh: "Refresh",
    process: "Process",
    uploading: "Uploading...",
    uploadPdf: "Upload PDF",
    collections: "Collections",
    allPapers: "All Papers",
    newCollection: "New Collection",
    uploadResults: "Upload Results",
    batchProcessing: "Batch Processing...",
    batchComplete: "Batch Complete",
    batchProcess: "Batch Process",
    noPapers: "No papers yet",
    noPapersDesc: "Upload PDFs to begin building your knowledge graph",
    table: {
      title: "Title",
      status: "Status",
      nodes: "Nodes",
      root: "Root",
      actions: "Actions",
    },
    status: {
      pending: "Pending",
      downloaded: "Downloaded",
      processed: "Processed",
      failed: "Failed",
    },
    progress: {
      success: "Success",
      failed: "Failed",
      remaining: "Est. remaining",
    },
  },

  // Concepts page
  concepts: {
    knowledgeGraph: "Knowledge Graph",
    conceptDetails: "Concept Details",
    concepts: "Concepts",
    clickToView: "Click concept to view actions",
    clickPaperToView: "Click paper to view details",
    nodeRepulsion: "Node Repulsion",
    compact: "Compact",
    spread: "Spread",
    backToAll: "Back to All Concepts",
    filter: "Filter",
    export: "Export",
    dedupScan: "Dedup Scan",
    legend: "Legend",
    conceptNode: "Concept Node",
    paperNode: "Paper Node",
    centerConcept: "Center Concept",
    discoverResearch: "Discover Research Points",
    viewPapers: "View Papers",
    paper: "papers",
    // Category labels
    category: {
      field: "Field",
      direction: "Direction",
      subdirection: "Subdirection",
      task: "Task",
      method: "Method",
      technique: "Technique",
      dataset: "Dataset",
      finding: "Finding",
    },
    // Filter panel
    filterPanel: {
      title: "Filter",
      searchPlaceholder: "Search concepts...",
      categoryFilter: "Category Filter",
      resetAll: "Reset All",
    },
    // Research points
    researchPoints: {
      title: "Research Points Discovery",
      basedOn: "Based on",
      analysis: "analysis",
      analysisContext: "Analysis Context",
      ancestors: "Ancestors",
      descendants: "Descendants",
      edgeNodes: "Edge Nodes",
      analyzing: "Analyzing knowledge graph...",
      traversing: "Traversing ancestors and edge nodes",
      discoveryMethod: "Discovery Method",
      researchValue: "Research Value",
      difficulty: "Difficulty basis",
      relatedConcepts: "Related Concepts",
      // Discovery methods
      method: {
        gap_filling: "Gap Filling",
        leaf_extension: "Leaf Extension",
        bottleneck: "Bottleneck Identification",
        transfer: "Transfer Application",
      },
      // Difficulty labels
      difficultyLabel: {
        low: "Easy",
        medium: "Med",
        high: "Hard",
      },
      // Novelty labels
      noveltyLabel: {
        high: "High",
        moderate: "Mod",
        incremental: "Inc",
      },
      // Impact labels
      impactLabel: {
        transformative: "Trans",
        broad: "Broad",
        niche: "Niche",
      },
    },
    // Paper detail panel
    paperDetail: {
      doi: "DOI",
      venue: "Venue",
      citations: "Citations",
      tldr: "TLDR (AI Summary)",
      authors: "Authors",
      keywords: "Keywords",
      abstract: "Abstract",
      keyContributions: "Key Contributions",
      more: "more",
    },
    // Recommendation panel
    recommendation: {
      title: "Paper Recommendations",
      basedOn: "Based on",
      concepts: "concepts",
      addConcept: "Add Concept",
      searchPapers: "Search Related Papers",
      combinedSearch: "Combined Search",
      singleSearch: "Single Search",
      loading: "Searching...",
      noResults: "No papers found",
      rateLimited: "API rate limited, please try again later",
      error: "Search error, please retry",
      year: "Year",
      minCitations: "Min Citations",
      allYears: "All",
      clearAll: "Clear All",
      openPdf: "Open PDF",
      viewOnS2: "View Details",
      addToGraph: "Add to Graph",
      selectedConcepts: "Selected",
      downloadAndProcess: "Download & Process",
      addMetadataOnly: "Add Metadata Only",
      processing: "Processing...",
      adding: "Adding...",
      added: "Added",
      addFailed: "Add failed",
    },
    // Citation graph panel
    citationGraph: {
      title: "Citation Graph",
      build: "Build Citation Graph",
      building: "Building...",
      refresh: "Refresh",
      noData: "No citation graph data",
      noDataDesc:
        'Click "Build Citation Graph" to fetch citations from Semantic Scholar',
      papers: "papers",
      edges: "citation edges",
      citing: "citing",
      citedBy: "cited by",
    },
  },

  // Modals
  modal: {
    close: "Close",
    cancel: "Cancel",
    save: "Save",
    create: "Create",
    test: "Test",
    goSettings: "Go to Settings",
    // LLM Config
    llmConfig: {
      title: "LLM Provider Configuration",
      configType: "Configuration Type",
      customConfig: "Custom Configuration",
      baseUrl: "Base URL",
      baseUrlPlaceholder: "https://api.openai.com/v1",
      baseUrlHint:
        "Supports OpenAI/Anthropic official APIs and compatible services",
      apiKey: "API Key",
      apiKeyPlaceholder: "sk-...",
      modelName: "Model Name",
      modelNamePlaceholder: "gpt-4o-mini, claude-3-5-sonnet-20241022...",
      testConnection: "Test Connection",
      saveConfig: "Save Configuration",
      saving: "Saving...",
      cliNotice:
        "Claude Code CLI is for local development only. Docker environments not supported.",
    },
    // S2 Config
    s2Config: {
      title: "Semantic Scholar",
      apiKey: "API Key",
      apiKeyPlaceholder: "Enter Semantic Scholar API Key",
      apiKeyHint: "Apply at",
      enableAuto: "Enable Auto-enhancement",
      configured: "API Key configured",
      enterNew: "Enter new key to replace",
    },
    // Create Folder
    createFolder: {
      title: "New Collection",
      name: "Collection Name",
      namePlaceholder: "e.g., Reinforcement Learning Papers",
      description: "Description (optional)",
      descPlaceholder: "Brief description of this collection",
      create: "Create Collection",
    },
    // Onboarding
    onboarding: {
      welcome: "Welcome to Meta Knowledge Graph",
      demo: "This demo includes 10 classic LLM papers to explore",
      features: {
        pdfUpload: "PDF Upload",
        pdfUploadDesc: "Upload papers and extract metadata automatically",
        conceptExtract: "Concept Extraction",
        conceptExtractDesc: "LLM builds hierarchical concept structures",
        graphInteract: "Interactive Graph",
        graphInteractDesc: "Drag, zoom, and click to explore relationships",
        researchDiscover: "Research Discovery",
        researchDiscoverDesc:
          "Find potential research directions from graph structure",
      },
      tip: "Tip: To process your own papers, configure an LLM API Key in settings first",
    },
  },

  // Dedup panel
  dedup: {
    title: "Concept Deduplication",
    scan: "Start Scan",
    scanning: "Scanning...",
    prefiltering: "Pre-filtering candidate pairs...",
    analyzing: "Analyzing candidate pairs...",
    batch: "Batch",
    progress: "Progress",
    estimatedTime: "Est. remaining",
    highConfidence: "high-confidence auto-merges",
    foundSuggestions: "Found",
    mergeSuggestions: "merge suggestions",
    noDuplicates: "No duplicate concepts found",
    papers: "Papers",
    rationale: "Rationale",
    executing: "Executing merges...",
    completed: "Completed",
    merges: "merges",
    fixedFloating: "fixed",
    floatingConcepts: "floating concepts",
    scanAgain: "Scan Again",
    executeSelected: "Execute Selected Merges",
  },

  // Export menu
  export: {
    html: "HTML Page",
    htmlDesc: "Interactive physics rendering",
    canvas: "Canvas Format",
    canvasDesc: "With colors and layout",
    markdown: "Markdown Format",
    markdownDesc: "Plain text with bidirectional links",
  },

  // Citation graph page
  citation: {
    title: "Citation Graph",
    build: "Build Citation Graph",
    building: "Building...",
    loading: "Loading citation graph...",
    refresh: "Refresh",
    noData: "No citation graph data",
    noDataDesc:
      'Click "Build Citation Graph" to fetch citations from Semantic Scholar',
    papers: "papers",
    edges: "citation edges",
    citing: "citing",
    citedBy: "cited by",
    citations: "citations",
    times: "times",
    moreEdges: "more edges",
    internalEdges: "Internal Citations",
    references: "References",
    citedByPapers: "Cited By",
    viewOnS2: "View on Semantic Scholar",
  },

  // Common
  common: {
    loading: "Loading...",
    all: "All",
    search: "Search",
    download: "Download",
    delete: "Delete",
    edit: "Edit",
    confirm: "Confirm",
    cancel: "Cancel",
    success: "Success",
    error: "Error",
    language: "Language",
    chinese: "中文",
    english: "English",
    retry: "Retry",
    back: "Back",
  },
};

export type Translation = typeof en;
