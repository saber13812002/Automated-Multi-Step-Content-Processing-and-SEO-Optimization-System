import { Client } from 'typesense';
import { getCollection } from '../src/config/chroma.js';
import { logger } from '../src/utils/logger.js';
import crypto from 'crypto';
import dotenv from 'dotenv';
import { openai, EMBEDDING_MODEL } from '../src/config/openai.js';

dotenv.config();

class KasrayarSearchScraper {
  constructor() {
    // Connect to kasrayar-search server
    this.typesenseClient = new Client({
      nodes: [{
        host: 'kasrayar-search.depna.com',
        port: '8108',
        protocol: 'https'
      }],
      apiKey: 'xyz', // Use the API key from your config
      connectionTimeoutSeconds: 30,
      requestTimeoutSeconds: 30,
      retryIntervalSeconds: 0.1,
      maxRetries: 3
    });
    
    this.collection = null;
    this.collectionAlt = null;
    this.processedCount = 0;
  }

  async initialize() {
    try {
      logger.info('🔗 Connecting to ChromaDB...');
      // Primary collection with 1536-dim (text-embedding-3-small)
      const primaryModel = process.env.EMBEDDING_MODEL_PRIMARY || 'text-embedding-3-small';
      const primaryName = process.env.CHROMA_COLLECTION_PRIMARY || 'kasra-docs-live';
      this.collection = await getCollection(primaryName, primaryModel);

      // Secondary collection with 3072-dim (text-embedding-3-large)
      const secondaryModel = process.env.EMBEDDING_MODEL_SECONDARY || 'text-embedding-3-large';
      const secondaryName = process.env.CHROMA_COLLECTION_SECONDARY || 'kasra-docs-live-3072';
      this.collectionAlt = await getCollection(secondaryName, secondaryModel);
      logger.info('✅ ChromaDB connection successful');
    } catch (error) {
      logger.error('❌ Failed to connect to ChromaDB:', error.message);
      throw error;
    }
  }

  async scrapeFromKasrayarSearch() {
    await this.initialize();
    
    try {
      logger.info('📋 Starting scrape from kasrayar-search.depna.com...');
      
      // Clear existing documents in both collections in ChromaDB
      await this.clearChromaCollection(this.collection);
      await this.clearChromaCollection(this.collectionAlt);
      
      // Get all documents from kasrayar-search Typesense
      let searchParams = {
        q: '*',
        per_page: 250,
        page: 1
      };
      
      let hasMore = true;
      let totalFound = 0;
      
      while (hasMore) {
        logger.info(`📖 Fetching page ${searchParams.page} from kasrayar-search...`);
        
        try {
          const results = await this.typesenseClient
            .collections('kasra-docs-live')
            .documents()
            .search(searchParams);
          
          if (results.hits && results.hits.length > 0) {
            totalFound = results.found;
            await this.processTypesenseDocuments(results.hits);
            
            // Check if there are more pages
            const totalPages = Math.ceil(results.found / searchParams.per_page);
            hasMore = searchParams.page < totalPages;
            searchParams.page++;
            
            logger.info(`📊 Progress: ${this.processedCount}/${totalFound} documents processed`);
          } else {
            hasMore = false;
          }
        } catch (searchError) {
          logger.error(`❌ Error fetching page ${searchParams.page}:`, searchError.message);
          hasMore = false;
        }
      }
      
      logger.info(`✅ Scraping completed! Processed ${this.processedCount} documents from ${totalFound} total`);
      
    } catch (error) {
      logger.error('❌ Scraping failed:', error.message);
      throw error;
    }
  }

  async processTypesenseDocuments(hits) {
    // First filter hits that have actual content
    const validHits = hits.filter(hit => {
      const doc = hit.document;
      return doc && (doc.content || doc.hierarchy?.lvl0 || doc.hierarchy?.lvl1 || doc.url);
    });
    
    const documents = validHits.map(hit => this.convertToChromaFormat(hit.document));
    
    // Filter out empty documents and documents without meaningful content
    const validDocuments = documents.filter(doc => {
      return doc.content.trim().length > 10 && doc.metadata.url; // At least 10 characters
    });
    
    if (validDocuments.length === 0) {
      logger.info('⚠️  No valid documents in this batch, skipping...');
      return;
    }
    
    // Generate embeddings for all documents at once for both models
    const texts = validDocuments.map(d => d.content);
    logger.info(`🤖 Generating embeddings (primary) for ${validDocuments.length} documents...`);
    const embeddingsPrimary = await this.generateEmbeddings(texts, process.env.EMBEDDING_MODEL_PRIMARY || 'text-embedding-3-small');

    logger.info(`🤖 Generating embeddings (secondary) for ${validDocuments.length} documents...`);
    const embeddingsSecondary = await this.generateEmbeddings(texts, process.env.EMBEDDING_MODEL_SECONDARY || 'text-embedding-3-large');

    // Add to ChromaDB primary
    await this.collection.add({
      ids: validDocuments.map(d => d.id),
      embeddings: embeddingsPrimary,
      documents: texts,
      metadatas: validDocuments.map(d => this.cleanMetadata(d.metadata))
    });

    // Add to ChromaDB secondary
    await this.collectionAlt.add({
      ids: validDocuments.map(d => `${d.id}-3072`),
      embeddings: embeddingsSecondary,
      documents: texts,
      metadatas: validDocuments.map(d => this.cleanMetadata(d.metadata))
    });

    this.processedCount += validDocuments.length;
    logger.info(`📦 Added ${validDocuments.length} documents to ChromaDB (both collections)`);
  }

  convertToChromaFormat(typesenseDoc) {
    // Extract hierarchical content
    const hierarchy = typesenseDoc.hierarchy || {};
    const content = typesenseDoc.content || '';
    const url = typesenseDoc.url || '';
    
    // Build hierarchical context
    const contextParts = [];
    if (hierarchy.lvl0) contextParts.push(hierarchy.lvl0);
    if (hierarchy.lvl1) contextParts.push(hierarchy.lvl1);
    if (hierarchy.lvl2) contextParts.push(hierarchy.lvl2);
    if (hierarchy.lvl3) contextParts.push(hierarchy.lvl3);
    
    const contextualContent = contextParts.length > 0 
      ? `${contextParts.join(' > ')}\n\n${content}`
      : content;
    
    // Generate document ID
    const docId = this.generateDocumentId(url, content);
    
    return {
      id: docId,
      content: contextualContent,
      metadata: {
        url: url || '',
        title: hierarchy.lvl0 || hierarchy.lvl1 || 'Untitled',
        section: hierarchy.lvl1 || '',
        subsection: hierarchy.lvl2 || '',
        heading: hierarchy.lvl3 || '',
        anchor: typesenseDoc.anchor || '',
        type: url.includes('/blog') ? 'blog' : 'docs',
        // Flatten hierarchy instead of nested object
        hierarchy_lvl0: hierarchy.lvl0 || '',
        hierarchy_lvl1: hierarchy.lvl1 || '',
        hierarchy_lvl2: hierarchy.lvl2 || '',
        hierarchy_lvl3: hierarchy.lvl3 || '',
        hierarchy_lvl4: hierarchy.lvl4 || '',
        hierarchy_lvl5: hierarchy.lvl5 || '',
        hierarchy_lvl6: hierarchy.lvl6 || '',
        lastIndexed: new Date().toISOString(),
        source: 'kasrayar-search-scraper',
        language: typesenseDoc.language || 'fa',
        version: typesenseDoc.version || ''
      }
    };
  }

  generateDocumentId(url, content) {
    // Add timestamp and random component to ensure uniqueness
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 8);
    
    const contentHash = crypto
      .createHash('md5')
      .update(content || timestamp.toString())
      .digest('hex')
      .substring(0, 8);
    
    const urlHash = crypto
      .createHash('md5')
      .update(url || random)
      .digest('hex')
      .substring(0, 8);
    
    return `kasrayar-${urlHash}-${contentHash}-${random}`;
  }

  cleanMetadata(metadata) {
    const cleaned = {};
    for (const [key, value] of Object.entries(metadata)) {
      // Only keep primitive values
      if (value === null || value === undefined) {
        cleaned[key] = '';
      } else if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
        cleaned[key] = value;
      } else {
        // Convert objects/arrays to string
        cleaned[key] = JSON.stringify(value);
      }
    }
    return cleaned;
  }

  async generateEmbeddings(texts, model) {
    try {
      // If no OpenAI key, use mock embeddings
      if (!process.env.OPENAI_API_KEY || process.env.USE_MOCK_EMBEDDINGS === 'true') {
        logger.info('⚠️  Using mock embeddings (no OpenAI API key or mock mode enabled)');
        const dim = model?.includes('large') ? 3072 : 1536;
        return texts.map(() => Array(dim).fill(0).map(() => Math.random() * 2 - 1));
      }
      
      // Batch process embeddings
      const batchSize = 20;
      const allEmbeddings = [];
      
      for (let i = 0; i < texts.length; i += batchSize) {
        const batch = texts.slice(i, i + batchSize);
        const response = await openai.embeddings.create({
          model: model || EMBEDDING_MODEL,
          input: batch
        });
        
        const embeddings = response.data.map(item => item.embedding);
        allEmbeddings.push(...embeddings);
        
        logger.info(`🔄 Generated embeddings: ${allEmbeddings.length}/${texts.length}`);
      }
      
      return allEmbeddings;
    } catch (error) {
      logger.error('Failed to generate embeddings:', error.message);
      logger.info('⚠️  Falling back to mock embeddings');
      const dim = model?.includes('large') ? 3072 : 1536;
      return texts.map(() => Array(dim).fill(0).map(() => Math.random() * 2 - 1));
    }
  }

  async clearChromaCollection(collection) {
    if (!collection) return;
    logger.info('🗑️  Clearing existing documents in ChromaDB...');
    try {
      const results = await collection.get();
      if (results.ids && results.ids.length > 0) {
        await collection.delete({ ids: results.ids });
        logger.info(`🗑️  Deleted ${results.ids.length} existing documents`);
      } else {
        logger.info('🗑️  ChromaDB collection is already empty');
      }
    } catch (error) {
      logger.info('🗑️  Collection cleared (was empty or didn\'t exist)');
    }
  }
}

// CLI execution
if (import.meta.url === `file://${process.argv[1]}`) {
  const scraper = new KasrayarSearchScraper();
  
  scraper.scrapeFromKasrayarSearch()
    .then(() => {
      logger.info('✅ Scraping from kasrayar-search completed successfully');
      process.exit(0);
    })
    .catch(error => {
      logger.error('❌ Scraping failed:', error);
      process.exit(1);
    });
}

export default KasrayarSearchScraper;
