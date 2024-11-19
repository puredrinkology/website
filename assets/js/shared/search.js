document.addEventListener('DOMContentLoaded', function() {
    let idx = null;  // Lunr index
    let searchResults = $('#search-results');
    let data = null; // Store search index data

    // Fetch search index JSON
    fetch('/searchindex/index.json')
        .then(response => response.json())
        .then(fetchedData => {
            data = fetchedData;  // Assign data to a higher scope
            // Create the Lunr index
            idx = lunr(function () {
                this.field('title');
                this.field('base_spirit');
                this.field('description');
                this.field('family');
                this.field('category');
                this.field('ingredient_items');
                this.ref('url');
                
                data.forEach(doc => {
                    this.add(doc);
                });
            });
        })
        .catch(error => console.error('Error fetching search index:', error));

    // Debounce function
    function debounce(func, delay) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    }

    // Search function
    const performSearch = debounce(function(query) {
        if (idx && query.length > 2) {
            const results = idx.search(query);
            searchResults.html('');  // Clear previous results

            if (results.length) {
                results.forEach(result => {
                    const url = result.ref;
                    const item = data.find(i => i.url === url); // Now data is available here
                    const cover = item.url + "images/cover.jpeg";
            
                    // only search cocktails for now!
                    if (item.category.toLowerCase() === "cocktail" || item.category.toLowerCase() === "mocktail") {
            
                        // Create the card container
                        var result = $('<div>', { class: 'col-12 col-md-4 col-lg-2 g-4' });
            
                        // Create the inner card structure
                        var card = $('<div>', {
                            class: 'card shadow border-0 p-4 text-decoration-none h-100',
                            style: 'border-radius: 15px;'
                        });
            
                        // Create the image container
                        var imgLink = $('<a>', {
                            class: 'aspect-ratio-full',
                            href: url,
                            title: item.title
                        });
            
                        // If there's a cover image, append it
                        if (cover) {
                            var img = $('<img>', {
                                class: 'rounded-10',
                                src: cover,
                                alt: item.title
                            });
                            imgLink.append(img);
                        }
            
                        // Create the card body
                        var cardBody = $('<div>', { class: 'card-body text-center' });
            
                        // Add the title
                        var cardTitle = $('<h5>', { class: 'card-title fw-semibold' });
                        var titleLink = $('<a>', {
                            href: url,
                            class: 'text-decoration-none',
                            text: item.title
                        });
                        cardTitle.append(titleLink);
                        cardBody.append(cardTitle);
            
                        // Add category badge
                        if (item.category) {
                            var categoryBadge = $('<a>', {
                                href: `/recipes/category/${item.category.toLowerCase()}/`,
                                class: 'badge text-bg-primary text-decoration-none mx-1',
                                text: item.category.toLowerCase(),
                                title: `The ${item.category} Collection`
                            });
                            cardBody.append(categoryBadge);
                        }
            
                        // Add base spirit badge
                        if (item.base_spirit) {
                            var spiritBadge = $('<a>', {
                                href: `/recipes/spirit/${item.base_spirit.toLowerCase()}/`,
                                class: 'badge text-bg-secondary text-decoration-none mx-1',
                                text: item.base_spirit.toLowerCase(),
                                title: `Cocktails made using ${item.base_spirit}`
                            });
                            cardBody.append(spiritBadge);
                        }
            
                        // Add family badge
                        if (item.family) {
                            var familyBadge = $('<a>', {
                                href: `/recipes/family/${item.family.toLowerCase()}/`,
                                class: 'badge text-bg-info text-decoration-none mx-1',
                                text: item.family.toLowerCase(),
                                title: `The ${item.family} Family`
                            });
                            cardBody.append(familyBadge);
                        }
            
                        // Append everything together
                        card.append(imgLink);
                        card.append(cardBody);
                        result.append(card);
            
                        // Append the final result to searchResults container
                        searchResults.append(result);
                    }
                });
            
                searchResults.addClass("p-4 pb-4");
            } else {
                searchResults.html('');
                searchResults.removeClass("p-4 pb-4")
            }
        } else {
                searchResults.html('');
                searchResults.removeClass("p-4 pb-4")
        }
    }, 300); // Adjust the delay as needed

    // Input event listener with debounced search
    document.getElementById('search-box').addEventListener('input', function() {
        const query = this.value;
        performSearch(query);  // Call the debounced search function
    });
});
