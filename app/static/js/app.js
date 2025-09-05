class TravelChatbot {
    constructor() {
        this.sessionId = null;
        this.isTyping = false;
        this.apiBaseUrl = window.location.origin;
        this.currentResults = [];
        this.currentMode = 'flight'; // 'flight' or 'hotel'
        
        this.initializeElements();
        this.initializeEventListeners();
        this.initializeTheme();
        this.initializeMode();
        this.checkConnection();
    }

    initializeElements() {
        // Chat elements
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.chatForm = document.getElementById('chatForm');
        this.sendButton = document.getElementById('sendButton');
        this.typingIndicator = document.getElementById('typingIndicator');
        
        // Results elements
        this.bookingResults = document.getElementById('bookingResults');
        this.resultsList = document.getElementById('resultsList');
        
        // Mode elements
        this.flightModeTab = document.getElementById('flightModeTab');
        this.hotelModeTab = document.getElementById('hotelModeTab');
        this.flightWelcome = document.getElementById('flightWelcome');
        this.hotelWelcome = document.getElementById('hotelWelcome');
        this.headerIcon = document.getElementById('headerIcon');
        this.headerTitle = document.getElementById('headerTitle');
        
        // Header elements
        this.clearChatBtn = document.getElementById('clearChat');
        this.toggleThemeBtn = document.getElementById('toggleTheme');
        this.connectionStatus = document.getElementById('connectionStatus');
        
        // Modal elements
        this.flightModal = document.getElementById('flightModal');
    }

    initializeEventListeners() {
        // Chat form listeners
        this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        this.messageInput.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.messageInput.addEventListener('input', () => this.autoResize());
        
        // Header listeners
        this.clearChatBtn.addEventListener('click', () => this.clearChat());
        this.toggleThemeBtn.addEventListener('click', () => this.toggleTheme());
        
        // Mode listeners
        this.flightModeTab.addEventListener('click', () => this.switchMode('flight'));
        this.hotelModeTab.addEventListener('click', () => this.switchMode('hotel'));
    }

    initializeTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        this.updateThemeIcon(savedTheme);
    }
    
    initializeMode() {
        this.switchMode('flight');
    }
    
    switchMode(mode) {
        this.currentMode = mode;
        
        // Update tab states
        if (mode === 'flight') {
            this.flightModeTab.classList.add('active');
            this.hotelModeTab.classList.remove('active');
            
            // Update welcome messages
            this.flightWelcome.style.display = 'block';
            this.hotelWelcome.style.display = 'none';
            
            // Update header
            this.headerIcon.className = 'fas fa-plane';
            
            // Update input placeholder
            this.messageInput.placeholder = "Ask me about flights (e.g., 'Find flights from NYC to Paris on March 15')";
            
            // Show/hide suggestions
            document.querySelectorAll('.flight-suggestion').forEach(el => el.style.display = 'inline-flex');
            document.querySelectorAll('.hotel-suggestion').forEach(el => el.style.display = 'none');
            
        } else if (mode === 'hotel') {
            this.hotelModeTab.classList.add('active');
            this.flightModeTab.classList.remove('active');
            
            // Update welcome messages
            this.flightWelcome.style.display = 'none';
            this.hotelWelcome.style.display = 'block';
            
            // Update header
            this.headerIcon.className = 'fas fa-bed';
            
            // Update input placeholder
            this.messageInput.placeholder = "Ask me about hotels (e.g., 'Find hotels in Mumbai from Dec 20 to 25')";
            
            // Show/hide suggestions
            document.querySelectorAll('.flight-suggestion').forEach(el => el.style.display = 'none');
            document.querySelectorAll('.hotel-suggestion').forEach(el => el.style.display = 'inline-flex');
        }
        
        // Clear chat when switching modes
        this.clearChat();
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        this.updateThemeIcon(newTheme);
    }

    updateThemeIcon(theme) {
        const icon = this.toggleThemeBtn.querySelector('i');
        icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }

    async checkConnection() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/health/`);
            if (response.ok) {
                this.setConnectionStatus(true);
            } else {
                this.setConnectionStatus(false);
            }
        } catch (error) {
            this.setConnectionStatus(false);
        }
    }

    setConnectionStatus(connected) {
        const statusText = this.connectionStatus.querySelector('span');
        if (connected) {
            this.connectionStatus.classList.add('connected');
            this.connectionStatus.classList.remove('disconnected');
            statusText.textContent = 'Connected';
        } else {
            this.connectionStatus.classList.remove('connected');
            this.connectionStatus.classList.add('disconnected');
            statusText.textContent = 'Disconnected';
        }
    }


    handleKeydown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.chatForm.dispatchEvent(new Event('submit'));
        }
    }

    autoResize() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;

        this.addMessage(message, 'user');
        this.messageInput.value = '';
        this.autoResize();
        this.showTypingIndicator();

        try {
            const response = await this.sendMessage(message);
            this.hideTypingIndicator();
            
            if (response.message) {
                // Debug logging
                console.log('Response received:', response);
                console.log('Data:', response.data);
                console.log('Show cards:', response.show_cards);
                console.log('Message type:', response.message_type);
                
                // Display combined message with recommendations and cards
                this.addMessage(response.message, 'assistant', response.data, response.show_cards, response.message_type);
            }
            
            if (response.data && response.data.length > 0) {
                this.currentResults = response.data;
            }
            
            if (response.session_id) {
                this.sessionId = response.session_id;
            }
        } catch (error) {
            this.hideTypingIndicator();
            this.showError('Failed to send message. Please try again.');
        }
    }

    async sendMessage(message) {
        const response = await fetch(`${this.apiBaseUrl}/api/chat/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: this.sessionId
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    displayResults(results, messageType) {
        if (!this.bookingResults || !this.resultsList) return;
        
        this.bookingResults.style.display = 'block';
        this.resultsList.innerHTML = '';
        
        if (messageType === 'flight_results') {
            results.forEach((flight, index) => {
                const flightCard = this.createFlightCard(flight, index);
                this.resultsList.appendChild(flightCard);
            });
        } else if (messageType === 'hotel_results') {
            results.forEach((hotel, index) => {
                const hotelCard = this.createHotelCard(hotel, index);
                this.resultsList.appendChild(hotelCard);
            });
        }
    }
    
    createFlightCard(flight, index) {
        const card = document.createElement('div');
        card.className = 'flight-card';
        
        const departureTime = new Date(flight['Departure']);
        const arrivalTime = new Date(flight['Arrival']);
        
        // Calculate flight duration
        const durationMs = arrivalTime.getTime() - departureTime.getTime();
        const durationHours = Math.floor(durationMs / (1000 * 60 * 60));
        const durationMins = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));
        const durationText = `${durationHours}h ${durationMins}m`;
        
        // Convert price to INR if EUR
        const priceInINR = flight['Currency'] === 'EUR' ? Math.floor(flight['Total Price'] * 90) : flight['Total Price'];
        const currency = flight['Currency'] === 'EUR' ? '₹' : flight['Currency'];
        
        card.innerHTML = `
            <div class="mmt-flight-card">
                <div class="flight-header">
                    <div class="airline-info">
                        <div class="airline-logo">${flight['Airline Code'] || 'AI'}</div>
                        <div class="airline-details">
                            <div class="airline-name">${flight['Airline Name'] || 'Air India'}</div>
                            <div class="flight-code">${flight['Airline Code'] || 'AI'}-${Math.floor(Math.random() * 9000) + 1000}</div>
                        </div>
                    </div>
                    <div class="flight-badges">
                        ${flight['Number of Stops'] === 0 ? '<span class="badge non-stop">Non stop</span>' : `<span class="badge stops">${flight['Number of Stops']} stop</span>`}
                    </div>
                </div>
                
                <div class="flight-route-info">
                    <div class="departure">
                        <div class="time">${departureTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                        <div class="date">${departureTime.toLocaleDateString('en-GB', {day: 'numeric', month: 'short'})}</div>
                        <div class="airport">BOM</div>
                    </div>
                    
                    <div class="flight-duration-info">
                        <div class="duration">${durationText}</div>
                        <div class="route-line">
                            <div class="line"></div>
                            <div class="stops-info">${flight['Number of Stops'] === 0 ? 'Direct' : `${flight['Number of Stops']} stop`}</div>
                        </div>
                    </div>
                    
                    <div class="arrival">
                        <div class="time">${arrivalTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                        <div class="date">${arrivalTime.toLocaleDateString('en-GB', {day: 'numeric', month: 'short'})}</div>
                        <div class="airport">DEL</div>
                    </div>
                </div>
                
                <div class="flight-pricing">
                    <div class="price-info">
                        <div class="price">${currency} ${priceInINR.toLocaleString()}</div>
                        <div class="price-note">per adult</div>
                    </div>
                    <button class="book-now-btn">
                        BOOK NOW
                    </button>
                </div>
            </div>
        `;
        
        // Add event listener for book button
        const bookBtn = card.querySelector('.book-now-btn');
        if (bookBtn) {
            bookBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showFlightDetails(flight);
            });
        }
        
        return card;
    }
    
    createHotelCard(hotel, index) {
        const card = document.createElement('div');
        card.className = 'hotel-card';
        
        // Parse price
        const priceValue = parseFloat(hotel['Total Price']) || 0;
        const currency = hotel['Currency'] || '₹';
        const priceDisplay = priceValue > 0 ? `${currency}${priceValue.toLocaleString()}` : 'Price on request';
        
        // Parse rating
        const rating = hotel['Rating'] && hotel['Rating'] !== 'N/A' ? parseFloat(hotel['Rating']) : 0;
        const ratingStars = rating > 0 ? '★'.repeat(Math.floor(rating)) + (rating % 1 ? '☆' : '') : 'No rating';
        
        // Clean amenities
        const amenities = hotel['Amenities'] || 'Standard amenities';
        const amenitiesList = amenities.split(',').slice(0, 3).join(', ');
        
        card.innerHTML = `
            <div class="hotel-card-content">
                <div class="hotel-header">
                    <div class="hotel-info">
                        <h3 class="hotel-name">${hotel['Hotel Name'] || 'Hotel'}</h3>
                        <div class="hotel-rating">
                            <span class="stars">${ratingStars}</span>
                            ${rating > 0 ? `<span class="rating-text">(${rating}/5)</span>` : ''}
                        </div>
                        <div class="hotel-location">
                            <i class="fas fa-map-marker-alt"></i>
                            <span>${hotel['City'] || ''} ${hotel['Country'] || ''}</span>
                        </div>
                    </div>
                    <div class="hotel-price">
                        <span class="price-amount">${priceDisplay}</span>
                        <span class="price-period">per night</span>
                    </div>
                </div>
                
                <div class="hotel-details">
                    <div class="room-type">
                        <i class="fas fa-bed"></i>
                        <span>${hotel['Room Type'] || 'Standard Room'}</span>
                    </div>
                    <div class="hotel-amenities">
                        <i class="fas fa-wifi"></i>
                        <span>${amenitiesList}</span>
                    </div>
                    <div class="check-times">
                        <span class="check-in">Check-in: ${hotel['Check-in Time'] || 'Standard'}</span>
                        <span class="check-out">Check-out: ${hotel['Check-out Time'] || 'Standard'}</span>
                    </div>
                </div>
                
                <div class="hotel-actions">
                    <button class="view-details-btn" onclick="showHotelDetails('${hotel['Hotel ID'] || ''}')">
                        <i class="fas fa-info-circle"></i>
                        View Details
                    </button>
                    <button class="book-now-btn">
                        <i class="fas fa-calendar-check"></i>
                        Book Now
                    </button>
                </div>
            </div>
        `;
        
        // Add event listener for book button
        const bookBtn = card.querySelector('.book-now-btn');
        if (bookBtn) {
            bookBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showHotelDetails(hotel);
            });
        }
        
        return card;
    }

    addMessage(text, sender, data = null, showCards = false, messageType = 'response') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = sender === 'user' ? 
            '<i class="fas fa-user"></i>' : 
            '<i class="fas fa-robot"></i>';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        const header = document.createElement('div');
        header.className = 'message-header';
        
        const senderName = document.createElement('span');
        senderName.className = 'message-sender';
        senderName.textContent = sender === 'user' ? 'You' : 'Assistant';
        
        const time = document.createElement('span');
        time.className = 'message-time';
        time.textContent = new Date().toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        header.appendChild(senderName);
        header.appendChild(time);
        
        const messageText = document.createElement('div');
        messageText.className = 'message-text';
        messageText.textContent = text;
        
        content.appendChild(header);
        
        // Debug logging for cards
        console.log('addMessage called with:', { showCards, data, dataLength: data ? data.length : 0, messageType });
        
        // Add cards FIRST if requested and data is available
        if (showCards && data && data.length > 0) {
            console.log(`Creating ${messageType === 'hotel_results' ? 'hotel' : 'flight'} cards...`);
            const cardsContainer = document.createElement('div');
            cardsContainer.className = messageType === 'hotel_results' ? 'inline-hotel-results' : 'inline-flight-results';
            
            const cardsHeader = document.createElement('div');
            cardsHeader.className = 'inline-results-header';
            const icon = messageType === 'hotel_results' ? 'fa-bed' : 'fa-plane';
            const title = messageType === 'hotel_results' ? 'Available Hotels' : 'Available Flights';
            cardsHeader.innerHTML = `
                <h4><i class="fas ${icon}"></i> ${title}</h4>
            `;
            cardsContainer.appendChild(cardsHeader);
            
            const cardsList = document.createElement('div');
            cardsList.className = messageType === 'hotel_results' ? 'inline-hotels-list' : 'inline-flights-list';
            
            data.forEach((item, index) => {
                let card;
                if (messageType === 'hotel_results') {
                    card = this.createHotelCard(item, index);
                } else {
                    card = this.createFlightCard(item, index);
                }
                cardsList.appendChild(card);
            });
            
            cardsContainer.appendChild(cardsList);
            content.appendChild(cardsContainer);
            
            // Add insights section after cards
            try {
                console.log('Parsing insights from response and data...');
                console.log('Full response text:', text);
                console.log('Data:', data);
                
                const insights = parseInsightsFromResponse(text, data);
                console.log('Insights parsed:', insights);
                
                // Create insights section dynamically for this message
                const insightsSection = createInsightsSection(insights);
                console.log('Insights section created:', insightsSection);
                content.appendChild(insightsSection);
                console.log('Insights displayed successfully');
            } catch (error) {
                console.error('Error displaying insights:', error);
                console.error('Error stack:', error.stack);
            }
        }
        
        // Then add the recommendations text below the cards
        // content.appendChild(messageText);
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        
        const welcomeMessage = this.chatMessages.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    showFlightDetails(flight) {
        const modalBody = document.getElementById('modalBody');
        const departureTime = new Date(flight['Departure']);
        const arrivalTime = new Date(flight['Arrival']);
        
        if (modalBody) {
            modalBody.innerHTML = `
                <div class="flight-detail">
                    <h4>Flight Information</h4>
                    <dl>
                        <dt>Airline:</dt>
                        <dd>${flight['Airline Name'] || flight['Airline Code']}</dd>
                        
                        <dt>Departure:</dt>
                        <dd>${departureTime.toLocaleString()}</dd>
                        
                        <dt>Arrival:</dt>
                        <dd>${arrivalTime.toLocaleString()}</dd>
                        
                        <dt>Price:</dt>
                        <dd>${flight['Currency']} ${flight['Total Price']}</dd>
                        
                        <dt>Cabin Class:</dt>
                        <dd>${flight['Cabin'] || 'Economy'}</dd>
                        
                        <dt>Stops:</dt>
                        <dd>${flight['Number of Stops'] === 0 ? 'Direct Flight' : `${flight['Number of Stops']} Stop(s)`}</dd>
                        
                        <dt>Trip Type:</dt>
                        <dd>${flight['One Way'] ? 'One Way' : 'Round Trip'}</dd>
                    </dl>
                </div>
            `;
        }
        
        this.flightModal.classList.add('active');
    }

    showTypingIndicator() {
        this.isTyping = true;
        this.typingIndicator.classList.add('active');
        this.sendButton.disabled = true;
    }

    hideTypingIndicator() {
        this.isTyping = false;
        this.typingIndicator.classList.remove('active');
        this.sendButton.disabled = false;
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 2rem;
            right: 2rem;
            background: var(--surface);
            border: 2px solid var(--${type === 'error' ? 'error' : 'primary'}-color);
            color: var(--text-primary);
            padding: 1rem 1.5rem;
            border-radius: var(--radius);
            box-shadow: var(--shadow-lg);
            z-index: 1001;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            max-width: 400px;
        `;
        
        notification.innerHTML = `
            <i class="fas fa-${type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
            <button onclick="this.parentElement.remove()" style="background: none; border: none; color: var(--text-secondary); cursor: pointer; margin-left: auto;">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    async clearChat() {
        if (!confirm('Are you sure you want to clear the chat history?')) return;
        
        if (this.sessionId) {
            try {
                await fetch(`${this.apiBaseUrl}/api/chat/session/${this.sessionId}`, {
                    method: 'DELETE'
                });
            } catch (error) {
                console.error('Failed to clear session:', error);
            }
        }
        
        this.sessionId = null;
        this.chatMessages.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">
                    <i class="fas fa-plane-departure"></i>
                </div>
                <h2>Flight Booking Assistant</h2>
                <p>I can help you find and compare flights. Just tell me:</p>
                <div class="features-list">
                    <div class="feature-item">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>Where you want to go</span>
                    </div>
                    <div class="feature-item">
                        <i class="fas fa-calendar-alt"></i>
                        <span>When you want to travel</span>
                    </div>
                    <div class="feature-item">
                        <i class="fas fa-users"></i>
                        <span>Number of passengers</span>
                    </div>
                </div>
                <div class="example-queries">
                    <h3>Try asking:</h3>
                    <button class="example-btn" onclick="sendExampleQuery('Find me flights from New York to London on December 15, 2024')">
                        <i class="fas fa-quote-left"></i>
                        Find me flights from New York to London on December 15, 2024
                    </button>
                    <button class="example-btn" onclick="sendExampleQuery('Show me the cheapest flights from Delhi to Mumbai next week')">
                        <i class="fas fa-quote-left"></i>
                        Show me the cheapest flights from Delhi to Mumbai next week
                    </button>
                    <button class="example-btn" onclick="sendExampleQuery('I need 2 tickets from San Francisco to Tokyo next Monday')">
                        <i class="fas fa-quote-left"></i>
                        I need 2 tickets from San Francisco to Tokyo next Monday
                    </button>
                </div>
            </div>
        `;
        
        if (this.flightResults) {
            this.flightResults.style.display = 'none';
        }
    }
}

// Global functions
function sendExampleQuery(query) {
    const input = document.getElementById('messageInput');
    input.value = query;
    input.focus();
    document.getElementById('chatForm').dispatchEvent(new Event('submit'));
}

function closeFlightModal() {
    document.getElementById('flightModal').classList.remove('active');
}

function closeComparisonModal() {
    document.getElementById('comparisonModal').classList.remove('active');
}

function scrollToSection(sectionId) {
    if (window.flightApp) {
        window.flightApp.scrollToSection(sectionId);
    }
}

function toggleFilters() {
    if (window.flightApp) {
        window.flightApp.toggleFilters();
    }
}

function toggleFlightComparison(index) {
    // Implementation for flight comparison
    console.log('Toggle comparison for flight', index);
}

function shareFlightDetails(index) {
    // Implementation for sharing flight details
    if (navigator.share) {
        navigator.share({
            title: 'Flight Details',
            text: 'Check out this flight I found!',
            url: window.location.href
        });
    } else {
        // Fallback - copy to clipboard
        navigator.clipboard.writeText(window.location.href);
        if (window.flightApp) {
            window.flightApp.showNotification('Flight details copied to clipboard!', 'success');
        }
    }
}

// Additional helper functions
function addSuggestion(text) {
    const input = document.getElementById('messageInput');
    input.value = text + ' ';
    input.focus();
}

// Flight Insights Functions
function switchInsightTab(tabName, clickedBtn) {
    console.log('Switching to tab:', tabName);
    
    // Get the parent insights container
    const insightsContainer = clickedBtn.closest('.flight-insights');
    console.log('Insights container found:', insightsContainer);
    
    // Remove active class from all tabs and content within this insights container
    insightsContainer.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        console.log('Removed active from tab:', btn);
    });
    insightsContainer.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
        console.log('Removed active from content:', content);
    });
    
    // Add active class to selected tab and content
    clickedBtn.classList.add('active');
    console.log('Added active to clicked button:', clickedBtn);
    
    const targetContent = insightsContainer.querySelector(`.tab-content[data-tab="${tabName}"]`);
    console.log('Target content element:', targetContent);
    
    if (targetContent) {
        targetContent.classList.add('active');
        console.log('Added active to target content');
    } else {
        console.error('Target content not found for tab:', tabName);
    }
}

function parseInsightsFromResponse(response, flightData) {
    console.log('Parsing insights from response:', response);
    
    const insights = {
        keyInsights: [],
        cheapest: null,
        fastest: null,
        bestValue: null,
        recommendations: {
            budget: 'Choose the most affordable option',
            business: 'Select direct flights for convenience',
            flexible: 'Consider flights with better timing'
        }
    };

    // Parse KEY_INSIGHTS section
    console.log('Looking for KEY_INSIGHTS markers...');
    const keyInsightsMatch = response.match(/KEY_INSIGHTS_START([\s\S]*?)KEY_INSIGHTS_END/);
    console.log('Key insights match:', keyInsightsMatch);
    if (keyInsightsMatch) {
        const insightsText = keyInsightsMatch[1];
        console.log('Insights text found:', insightsText);
        const insightLines = insightsText.split('\n')
            .map(line => line.trim())
            .filter(line => line.startsWith('-'))
            .map(line => line.replace(/^-\s*/, ''));
        insights.keyInsights = insightLines;
        console.log('Parsed key insights:', insights.keyInsights);
    } else {
        console.log('No KEY_INSIGHTS markers found in response');
    }

    // Parse COMPARISON section
    const comparisonMatch = response.match(/COMPARISON_START([\s\S]*?)COMPARISON_END/);
    if (comparisonMatch) {
        const comparisonText = comparisonMatch[1];
        const lines = comparisonText.split('\n').map(line => line.trim()).filter(line => line);
        
        lines.forEach(line => {
            if (line.includes('cheapest:')) {
                const price = line.split('cheapest:')[1].trim();
                insights.cheapest = { price, details: 'Most affordable option' };
            }
            if (line.includes('fastest:')) {
                const time = line.split('fastest:')[1].trim();
                insights.fastest = { time, details: 'Shortest travel time' };
            }
            if (line.includes('bestValue:')) {
                const value = line.split('bestValue:')[1].trim();
                insights.bestValue = { details: value };
            }
        });
        console.log('Parsed comparison data:', { cheapest: insights.cheapest, fastest: insights.fastest, bestValue: insights.bestValue });
    }

    // Parse RECOMMENDATIONS section
    const recommendationsMatch = response.match(/RECOMMENDATIONS_START([\s\S]*?)RECOMMENDATIONS_END/);
    if (recommendationsMatch) {
        const recommendationsText = recommendationsMatch[1];
        const lines = recommendationsText.split('\n').map(line => line.trim()).filter(line => line);
        
        lines.forEach(line => {
            if (line.includes('budget:')) {
                insights.recommendations.budget = line.split('budget:')[1].trim();
            }
            if (line.includes('business:')) {
                insights.recommendations.business = line.split('business:')[1].trim();
            }
            if (line.includes('flexible:')) {
                insights.recommendations.flexible = line.split('flexible:')[1].trim();
            }
        });
        console.log('Parsed recommendations:', insights.recommendations);
    }

    // Fallback: if no structured data found, use flight data for basic insights
    if (insights.keyInsights.length === 0 && flightData && flightData.length > 0) {
        console.log('No structured insights found, generating fallback insights from flight data');
        
        // Find cheapest flight
        const cheapestFlight = flightData.reduce((min, flight) => 
            parseFloat(flight['Total Price']) < parseFloat(min['Total Price']) ? flight : min
        );
        
        // Calculate duration for each flight and find fastest
        const flightsWithDuration = flightData.map(flight => {
            const dept = new Date(flight.Departure);
            const arr = new Date(flight.Arrival);
            const duration = (arr - dept) / (1000 * 60); // duration in minutes
            return { ...flight, durationMinutes: duration };
        });
        
        const fastestFlight = flightsWithDuration.reduce((fastest, flight) => 
            flight.durationMinutes < fastest.durationMinutes ? flight : fastest
        );

        // Set fallback data
        insights.cheapest = {
            price: `₹${parseFloat(cheapestFlight['Total Price']).toLocaleString()}`,
            details: `${cheapestFlight['Airline Name']} (${cheapestFlight['Airline Code']})`
        };

        const fastestHours = Math.floor(fastestFlight.durationMinutes / 60);
        const fastestMins = Math.round(fastestFlight.durationMinutes % 60);
        insights.fastest = {
            time: `${fastestHours}h ${fastestMins}m`,
            details: fastestFlight['Number of Stops'] === 0 ? 'Direct Flight' : `${fastestFlight['Number of Stops']} stop(s)`
        };

        insights.bestValue = {
            details: 'Best balance of price and convenience'
        };

        insights.keyInsights = [
            `Cheapest flight starts from ₹${parseFloat(cheapestFlight['Total Price']).toLocaleString()}`,
            `Fastest flight takes ${fastestHours}h ${fastestMins}m`,
            `${flightData.length} total flight options available`,
            `Multiple airlines and timing options to choose from`
        ];
    }

    console.log('Final parsed insights:', insights);
    return insights;
}

function createInsightsSection(insights) {
    console.log('Creating insights section with:', insights);
    
    const insightsContainer = document.createElement('div');
    insightsContainer.className = 'flight-insights';
    insightsContainer.style.marginTop = '1rem';
    
    // Create tabs
    const tabsDiv = document.createElement('div');
    tabsDiv.className = 'insights-tabs';
    tabsDiv.innerHTML = `
        <button class="tab-btn active" onclick="switchInsightTab('insights', this)">
            <i class="fas fa-lightbulb"></i>
            Key Insights
        </button>
        <button class="tab-btn" onclick="switchInsightTab('comparison', this)">
            <i class="fas fa-chart-bar"></i>
            Quick Comparison
        </button>
        <button class="tab-btn" onclick="switchInsightTab('recommendations', this)">
            <i class="fas fa-thumbs-up"></i>
            Recommendations
        </button>
    `;
    console.log('Created tabs div:', tabsDiv);
    
    // Create content area
    const contentDiv = document.createElement('div');
    contentDiv.className = 'insights-content';
    
    // Key Insights Tab
    const insightsTab = document.createElement('div');
    insightsTab.className = 'tab-content active';
    insightsTab.setAttribute('data-tab', 'insights');
    console.log('Created insights tab with data-tab:', insightsTab.getAttribute('data-tab'));
    
    const insightsList = document.createElement('div');
    insightsList.className = 'insights-list';
    
    if (insights.keyInsights && insights.keyInsights.length > 0) {
        insights.keyInsights.forEach(insight => {
            const insightDiv = document.createElement('div');
            insightDiv.className = 'insight-item';
            insightDiv.innerHTML = `
                <div class="insight-icon">
                    <i class="fas fa-lightbulb"></i>
                </div>
                <div class="insight-text">${insight}</div>
            `;
            insightsList.appendChild(insightDiv);
        });
    } else {
        // Add fallback content if no insights found
        const noInsightsDiv = document.createElement('div');
        noInsightsDiv.className = 'insight-item';
        noInsightsDiv.innerHTML = `
            <div class="insight-icon">
                <i class="fas fa-info-circle"></i>
            </div>
            <div class="insight-text">No specific insights available. Check the flight options above for details.</div>
        `;
        insightsList.appendChild(noInsightsDiv);
    }
    
    insightsTab.appendChild(insightsList);
    
    // Quick Comparison Tab
    const comparisonTab = document.createElement('div');
    comparisonTab.className = 'tab-content';
    comparisonTab.setAttribute('data-tab', 'comparison');
    console.log('Created comparison tab with data-tab:', comparisonTab.getAttribute('data-tab'));
    comparisonTab.innerHTML = `
        <div class="comparison-cards">
            <div class="comparison-card cheapest">
                <div class="card-header">CHEAPEST</div>
                <div class="card-value">${insights.cheapest?.price || 'Check options above'}</div>
                <div class="card-detail">${insights.cheapest?.details || 'Most affordable option'}</div>
            </div>
            <div class="comparison-card fastest">
                <div class="card-header">FASTEST</div>
                <div class="card-value">${insights.fastest?.time || 'Check durations above'}</div>
                <div class="card-detail">${insights.fastest?.details || 'Shortest travel time'}</div>
            </div>
            <div class="comparison-card best-value">
                <div class="card-header">BEST VALUE</div>
                <div class="card-value">
                    <i class="fas fa-star"></i>
                    <i class="fas fa-star"></i>
                    <i class="fas fa-star"></i>
                    <i class="fas fa-star"></i>
                    <i class="fas fa-star"></i>
                </div>
                <div class="card-detail">${insights.bestValue?.details || 'Best value option'}</div>
            </div>
        </div>
    `;
    
    // Recommendations Tab
    const recommendationsTab = document.createElement('div');
    recommendationsTab.className = 'tab-content';
    recommendationsTab.setAttribute('data-tab', 'recommendations');
    console.log('Created recommendations tab with data-tab:', recommendationsTab.getAttribute('data-tab'));
    recommendationsTab.innerHTML = `
        <div class="recommendation-cards">
            <div class="recommendation-card budget">
                <div class="card-icon">
                    <i class="fas fa-wallet"></i>
                </div>
                <div class="card-content">
                    <h4>Budget Travelers</h4>
                    <p>${insights.recommendations?.budget || 'Choose the most affordable option'}</p>
                </div>
            </div>
            <div class="recommendation-card business">
                <div class="card-icon">
                    <i class="fas fa-briefcase"></i>
                </div>
                <div class="card-content">
                    <h4>Business Travelers</h4>
                    <p>${insights.recommendations?.business || 'Select direct flights for convenience'}</p>
                </div>
            </div>
            <div class="recommendation-card flexible">
                <div class="card-icon">
                    <i class="fas fa-sun"></i>
                </div>
                <div class="card-content">
                    <h4>Flexible Schedule</h4>
                    <p>${insights.recommendations?.flexible || 'Consider flights with better timing'}</p>
                </div>
            </div>
        </div>
    `;
    
    // Assemble the insights section
    contentDiv.appendChild(insightsTab);
    contentDiv.appendChild(comparisonTab);
    contentDiv.appendChild(recommendationsTab);
    
    insightsContainer.appendChild(tabsDiv);
    insightsContainer.appendChild(contentDiv);
    
    console.log('Final insights container created:', insightsContainer);
    console.log('Content tabs in container:', insightsContainer.querySelectorAll('.tab-content'));
    console.log('Tab buttons in container:', insightsContainer.querySelectorAll('.tab-btn'));
    
    return insightsContainer;
}

// Test function to check parsing with the exact response
function testParsing() {
    const testResponse = `🎯 Best Deal
Price: ₹4067
Airline: AIR INDIA (AI)
Time: 11:00 - 11:50
Stops: 1 stop
Duration: 50m

✈️ Available Flights

Option 1
Airline: AIR INDIA (AI)
Price: ₹4067
Departure: 11:00
Arrival: 11:50
Stops: 1 stop

Option 2
Airline: AIR INDIA (AI)  
Price: ₹4067
Departure: 18:00
Arrival: 20:00
Stops: 1 stop

Option 3
Airline: AIR INDIA (AI)  
Price: ₹4858
Departure: 21:10
Arrival: 23:35
Stops: Direct

Option 4
Airline: AIR INDIA (AI)  
Price: ₹5524
Departure: 12:35
Arrival: 14:50
Stops: Direct

Option 5
Airline: AIR INDIA (AI)  
Price: ₹5524
Departure: 11:40
Arrival: 14:05
Stops: Direct

KEY_INSIGHTS_START
- Cheapest flights available from ₹4067
- Price range: ₹4067 to ₹5968
- All flights require 1 stop except two
- Morning departures offer good timing
KEY_INSIGHTS_END

COMPARISON_START
cheapest: ₹4067
fastest: 50m
bestValue: Best balance of price and convenience
COMPARISON_END

RECOMMENDATIONS_START
budget: Choose the morning flight at ₹4067 for best value
business: Consider the evening flight for convenience  
flexible: Morning departure offers more flexibility for connections
RECOMMENDATIONS_END`;

    console.log('Testing parsing with exact response...');
    const result = parseInsightsFromResponse(testResponse, []);
    console.log('Test result:', result);
    
    if (result.keyInsights.length > 0) {
        console.log('✅ Key insights parsed successfully');
    } else {
        console.log('❌ Key insights parsing failed');
    }
    
    if (result.cheapest && result.fastest) {
        console.log('✅ Comparison data parsed successfully');
    } else {
        console.log('❌ Comparison data parsing failed');
    }
    
    if (result.recommendations.budget !== 'Choose the most affordable option') {
        console.log('✅ Recommendations parsed successfully');
    } else {
        console.log('❌ Recommendations parsing failed');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.chatbot = new TravelChatbot();
    
    // Add test function to window for debugging
    window.testParsing = testParsing;
    
    setInterval(() => {
        window.chatbot.checkConnection();
    }, 30000);
});