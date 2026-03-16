export type Locale = "ja" | "vi";

export interface Translations {
  // Common
  common: {
    search: string;
    sync: string;
    login: string;
    logout: string;
    back: string;
    home: string;
    loading: string;
    error: string;
    view: string;
    generating: string;
  };

  // Header
  header: {
    menu: string;
    search: string;
    voiceSearch: string;
    notifications: string;
    accountMenu: string;
  };

  // Sidebar
  sidebar: {
    home: string;
    new: string;
    myPage: string;
    history: string;
    watchLater: string;
    likedVideos: string;
    categories: string;
    admin: string;
    administrator: string;
    copyright: string;
  };

  // User menu
  userMenu: {
    watchHistory: string;
    admin: string;
  };

  // New page
  new: {
    subtitle: string;
    noVideos: string;
  };

  // Home page
  home: {
    all: string;
    searchResults: string;
    videosCount: string;
    noVideos: string;
    noVideosSearch: string;
    noVideosCategory: string;
    noVideosSync: string;
    categorySecurity: string;
    categoryDevelopment: string;
    categoryInfrastructure: string;
    categoryCommunication: string;
    categoryMisc: string;
  };

  // Video card
  videoCard: {
    views: string;
    today: string;
    daysAgo: string;
    weeksAgo: string;
    monthsAgo: string;
    yearsAgo: string;
  };

  // Login
  login: {
    title: string;
    subtitle: string;
    description: string;
    loginWithGitHub: string;
    mockLogin: string;
    authOpensInNewTab: string;
    authErrorCancelled: string;
    authError: string;
    forEngineers: string;
  };

  // Admin
  admin: {
    title: string;
    subtitle: string;
    totalArticles: string;
    publishedVideos: string;
    generating: string;
    errors: string;
    wikiSync: string;
    lastSync: string;
    commitHash: string;
    processedArticles: string;
    sync: string;
    fullResync: string;
    notebookLMAuth: string;
    notebookLMDesc: string;
    reLogin: string;
    articlesVideos: string;
    noArticles: string;
    syncFirst: string;
    authenticated: string;
    sessionExpired: string;
    notLoggedIn: string;
    published: string;
    generatingStatus: string;
    errorStatus: string;
    notGenerated: string;
    syncComplete: string;
    noChanges: string;
    syncStarted: string;
    createFromDirectory: string;
    selectDirectory: string;
    createVideos: string;
    noDirectories: string;
  };

  // Watch later
  watchLater: {
    title: string;
    loginRequired: string;
    loginRequiredDesc: string;
    noVideos: string;
    noVideosDesc: string;
    findVideos: string;
  };

  // Liked videos
  liked: {
    title: string;
    loginRequired: string;
    loginRequiredDesc: string;
    noVideos: string;
    noVideosDesc: string;
    findVideos: string;
  };

  // History
  history: {
    title: string;
    loginRequired: string;
    loginRequiredDesc: string;
    recordsCount: string;
    noHistory: string;
    noHistoryDesc: string;
    emptySubtitle: string;
    findVideos: string;
    watched: string;
    justNow: string;
    minsAgo: string;
    hoursAgo: string;
    daysAgo: string;
    unknownTitle: string;
  };

  // Video detail
  videoDetail: {
    addToWatchLater: string;
    removeFromWatchLater: string;
    addToLiked: string;
    removeFromLiked: string;
    loading: string;
    notFound: string;
    backToHome: string;
    videoPreview: string;
    videoPreviewDesc: string;
    watched: string;
    markWatched: string;
    published: string;
    showMarkdown: string;
    markdownNote: string;
    relatedVideos: string;
    relatedVideosFallback: string;
    min: string;
    sec: string;
    viewers: string;
    views: string;
  };

  // Theme
  theme: {
    lightMode: string;
    darkMode: string;
  };
}
